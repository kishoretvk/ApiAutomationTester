import streamlit as st
import os
import pandas as pd
import time
import json
import numpy as np
import logging
from input_handler import load_questions
from api_client import ApiClient, RateLimiter
from state_manager import load_state, save_state, is_processed, mark_as_processed
from output_writer import write_result

st.set_page_config(layout="wide")
st.title("API Processing Metrics")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize session state
if 'metrics' not in st.session_state:
    st.session_state.metrics = {
        'total_questions': 0,
        'api_metrics': {},
        'start_time': None,
        'end_time': None,
        'processing_running': False,
        'stop_processing': False,
        'attempt_count': 0
    }

# Simplified processing function
def process_questions(questions, api_configs):
    st.session_state.metrics['processing_running'] = True
    st.session_state.metrics['stop_processing'] = False
    st.session_state.metrics['start_time'] = time.time()
    st.session_state.metrics['total_questions'] = len(questions)
    
    for api_config in api_configs:
        api_name = api_config.get("name", "Unnamed API")
        if api_name not in st.session_state.metrics['api_metrics']:
            st.session_state.metrics['api_metrics'][api_name] = {
                'processed': 0,
                'errors': 0,
                'latencies': [],
                'payload_sizes': []
            }
    
    # Process questions (simplified version)
    for i, question in enumerate(questions):
        if st.session_state.metrics['stop_processing']:
            break
            
        for api_config in api_configs:
            api_name = api_config.get("name", "Unnamed API")
            try:
                # Call API and process result
                result, latency, payload_size = ApiClient(api_config).call_api(question)
                st.session_state.metrics['api_metrics'][api_name]['processed'] += 1
                st.session_state.metrics['api_metrics'][api_name]['latencies'].append(latency)
                st.session_state.metrics['api_metrics'][api_name]['payload_sizes'].append(payload_size)
                write_result(f"{api_name}_results.jsonl", result)
            except Exception as e:
                st.session_state.metrics['api_metrics'][api_name]['errors'] += 1
                logging.error(f"Error processing question {i} with API {api_name}: {e}")
                
        time.sleep(0.1)  # Small delay to prevent UI freeze
    
    st.session_state.metrics['end_time'] = time.time()
    st.session_state.metrics['processing_running'] = False

# Display metrics
def display_metrics():
    metrics = st.session_state.metrics
    st.subheader("Processing Metrics")
    
    if metrics['processing_running']:
        elapsed = time.time() - metrics['start_time']
        st.metric("Processing Time", f"{elapsed:.2f}s")
    elif metrics['end_time']:
        total_time = metrics['end_time'] - metrics['start_time']
        st.metric("Total Processing Time", f"{total_time:.2f}s")
    
    for api_name, api_metrics in metrics['api_metrics'].items():
        st.write(f"**{api_name}**")
        col1, col2, col3 = st.columns(3)
        col1.metric("Processed", api_metrics['processed'])
        col2.metric("Errors", api_metrics['errors'])
        if api_metrics['latencies']:
            avg_latency = np.mean(api_metrics['latencies'])
            col3.metric("Avg Latency", f"{avg_latency:.2f}s")

# Main UI
uploaded_file = st.file_uploader("Upload input file", type=["txt", "csv", "xlsx"])
if uploaded_file:
    questions = load_questions(uploaded_file)
    if questions:
        st.success(f"Loaded {len(questions)} questions")
        
        if st.button("Start Processing") and not st.session_state.metrics['processing_running']:
            process_questions(questions, st.session_state.get('api_configs', []))
            
        if st.button("Stop Processing") and st.session_state.metrics['processing_running']:
            st.session_state.metrics['stop_processing'] = True

display_metrics()

# Auto-refresh every 5 seconds
if st.session_state.metrics['processing_running']:
    time.sleep(5)
    st.experimental_rerun()
