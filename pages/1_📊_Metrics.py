import streamlit as st
import os
import pandas as pd
import time
import json
import numpy as np
import logging
import asyncio
from input_handler import load_questions, APIHandler
from output_writer import write_api_log, write_api_metrics
from api_logger import APILogger
from tenacity import retry, stop_after_attempt, wait_exponential

st.set_page_config(layout="wide")
st.title("API Processing Metrics")

# --- Reset Button ---
if st.button("Reset Metrics & Clear File", key="reset_metrics_button", type="secondary"):
    st.session_state.metrics = {
        'total_questions': 0,
        'api_metrics': {},
        'start_time': None,
        'end_time': None,
        'processing_running': False,
        'stop_processing': False,
    }
    if "file_uploader" in st.session_state:
        st.session_state.file_uploader = None
    st.success("Metrics reset and file cleared.")
    st.rerun()

# Initialize metrics
if 'metrics' not in st.session_state:
    st.session_state.metrics = {
        'total_questions': 0,
        'api_metrics': {},
        'start_time': None,
        'end_time': None,
        'processing_running': False,
        'stop_processing': False,
    }

# File uploader with session state key management
if 'file_uploader_key' not in st.session_state:
    st.session_state.file_uploader_key = 0
    
uploaded_file = st.file_uploader("Upload input file", 
                               type=["txt", "csv", "xlsx"],
                               key=f"file_uploader_{st.session_state.file_uploader_key}")

# Initialize questions variable
questions = None

if uploaded_file:
    file_type = uploaded_file.name.split('.')[-1].lower()
    column_name = None
    if file_type in ['csv', 'xlsx']:
        column_name = st.text_input("Enter the column name containing questions", 
                                  value="question", 
                                  key="column_name_input")

    try:
        questions = load_questions(uploaded_file, file_type, column_name)
        if questions:
            st.success(f"Loaded {len(questions)} questions successfully.")
        else:
            st.warning("No questions loaded - check file format and content")
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        questions = None

# Metrics display function
def display_metrics():
    metrics = st.session_state.metrics
    st.subheader("Processing Metrics")

    if metrics.get('processing_running', False):
        elapsed = time.time() - metrics.get('start_time', time.time())
        st.metric("Processing Time Elapsed", f"{elapsed:.2f}s")
    elif metrics.get('end_time') and metrics.get('start_time'):
        total_time = metrics['end_time'] - metrics['start_time']
        st.metric("Total Processing Time", f"{total_time:.2f}s")

    st.metric("Total Questions", metrics.get('total_questions', 0))

    for api_name, api_metrics in metrics.get('api_metrics', {}).items():
        st.write(f"**{api_name}**")
        cols = st.columns(3)
        cols[0].metric("Processed", api_metrics.get('processed', 0))
        cols[1].metric("Errors", api_metrics.get('errors', 0))
        cols[2].metric("Success Rate", f"{api_metrics.get('success_rate', 0):.1f}%")

        if api_metrics.get('status_codes'):
            st.bar_chart(pd.DataFrame.from_dict(
                api_metrics['status_codes'], 
                orient='index',
                columns=['Count']
            ))

async def process_question(api_handler, api_config, question):
    """Process a single question through an API configuration"""
    api_name = api_config.get("name", "Unnamed API")
    try:
        headers = json.loads(api_config.get('headers', '{}'))
        payload = json.loads(api_config.get('payload', '{}'))
        
        # Insert question into payload using configured key
        payload_key = api_config.get('payload_key', 'user_input')
        payload[payload_key] = question

        # Make async API call
        method = api_config.get('method', 'POST').lower()
        url = api_config.get('url', '')
        
        # Configure API handler based on SSL settings
        api_handler.disable_verify = api_config.get('disable_ssl_verify', False)
        
        request_args = {
            "headers": headers,
            "json": payload
        }

        if api_config.get('auth_config', {}).get('current_token'):
            request_args['headers']['Authorization'] = f"Bearer {api_config['auth_config']['current_token']}"

        start_time = time.time()
        try:
            response = await api_handler.make_request(method, url, **request_args)
            
            # Handle different response types
            status_code = 200
            if isinstance(response, dict):
                status_code = response.get('status_code', 200)
            elif hasattr(response, 'status'):  # Handle aiohttp response
                status_code = response.status
            
            # Update metrics
            processing_time = time.time() - start_time
            return {
                "success": True,
                "api_name": api_name,
                "status_code": status_code,
                "processing_time": processing_time,
                "payload_size": len(str(response))
            }
        except Exception as e:
            logging.error(f"API call failed for {api_name}: {str(e)}")
            return {
                "success": False,
                "api_name": api_name,
                "error": str(e),
                "processing_time": time.time() - start_time
            }

    except Exception as e:
        logging.error(f"Error processing {api_name}: {str(e)}")
        return {
            "success": False,
            "api_name": api_name,
            "error": str(e)
        }

async def process_batch(api_configs, questions, progress_bar, batch_size=10):
    """Process questions in batches with progress tracking"""
    total = len(questions) * len(api_configs)
    processed = 0
    
    async with APIHandler() as api_handler:
        for i in range(0, len(questions), batch_size):
            batch = questions[i:i+batch_size]
            tasks = []
            
            for api_config in api_configs:
                for q in batch:
                    tasks.append(process_question(api_handler, api_config, q))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                processed += 1
                progress = processed / total
                progress_bar.progress(progress)
                
                if isinstance(result, Exception):
                    logging.error(f"Processing error: {str(result)}")
                    continue
                    
                # Update metrics
                api_name = result['api_name']
                api_metrics = st.session_state.metrics['api_metrics'][api_name]
                
                if result['success']:
                    api_metrics['processed'] += 1
                    api_metrics['status_codes'][str(result['status_code'])] = (
                        api_metrics['status_codes'].get(str(result['status_code']), 0) + 1
                    )
                else:
                    api_metrics['errors'] += 1

# Processing controls
if questions:
    col_start, col_stop = st.columns(2)
    with col_start:
        if st.button("Start Processing", disabled=st.session_state.metrics.get('processing_running', False)):
            st.session_state.metrics.update({
                'processing_running': True,
                'stop_processing': False,
                'start_time': time.time(),
                'total_questions': len(questions),
                'api_metrics': {
                    cfg['name']: {
                        'processed': 0,
                        'errors': 0,
                        'success_rate': 0,
                        'status_codes': {},
                        'timestamps': []
                    } for cfg in st.session_state.get('api_configs', [])
                }
            })
            progress_bar = st.progress(0)
            asyncio.run(process_batch(
                st.session_state.get('api_configs', []),
                questions,
                progress_bar
            ))
            st.session_state.metrics.update({
                'processing_running': False,
                'end_time': time.time()
            })
            st.rerun()

    with col_stop:
        if st.button("Stop Processing", disabled=not st.session_state.metrics.get('processing_running', False)):
            st.session_state.metrics['stop_processing'] = True
            st.warning("Processing will stop after current batch")

# Display metrics
display_metrics()

# Auto-refresh if processing
if st.session_state.metrics.get('processing_running', False):
    time.sleep(1)
    st.rerun()
