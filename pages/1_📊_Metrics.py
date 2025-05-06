import streamlit as st
import os
import pandas as pd
import time
import json
import numpy as np
import logging
import requests # Ensure requests is imported

from input_handler import load_questions
from output_writer import write_api_log, write_api_metrics
from api_logger import APILogger

st.set_page_config(layout="wide")
st.title("API Processing Metrics")

# --- Reset Button ---
if st.button("Reset Metrics & Clear File", key="reset_metrics_button", type="secondary"):
    # Reset metrics dictionary
    st.session_state.metrics = {
        'total_questions': 0,
        'api_metrics': {},
        'start_time': None,
        'end_time': None,
        'processing_running': False,
        'stop_processing': False,
    }
    # Clear the file uploader state by setting its key in session_state to None
    if "file_uploader" in st.session_state:
        st.session_state.file_uploader = None
    st.success("Metrics reset and file cleared.")
    # Use st.rerun() to reflect the changes immediately
    try:
        st.rerun()
    except AttributeError:
        st.warning("Could not automatically rerun page after reset.")

st.divider()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize session state for metrics if not already present
if 'metrics' not in st.session_state:
    st.session_state.metrics = {
        'total_questions': 0,
        'api_metrics': {}, # Stores metrics per API like {'API Name': {'processed': 0, 'errors': 0}}
        'start_time': None,
        'end_time': None,
        'processing_running': False,
        'stop_processing': False,
    }

# Function to display metrics (simplified based on current state structure)
def display_metrics():
    metrics = st.session_state.metrics
    st.subheader("Processing Metrics")

    if metrics.get('processing_running', False):
        elapsed = time.time() - metrics.get('start_time', time.time())
        st.metric("Processing Time Elapsed", f"{elapsed:.2f}s")
    elif metrics.get('end_time') and metrics.get('start_time'):
        total_time = metrics['end_time'] - metrics['start_time']
        st.metric("Total Processing Time", f"{total_time:.2f}s")
    else:
         st.metric("Processing Time", "N/A")

    st.metric("Total Questions", metrics.get('total_questions', 0))

    for api_name, api_metrics_data in metrics.get('api_metrics', {}).items():
        st.write(f"**{api_name}**")
        
        # Main metrics row
        col1, col2, col3 = st.columns(3)
        col1.metric("Processed", api_metrics_data.get('processed', 0))
        col2.metric("Errors", api_metrics_data.get('errors', 0))
        col3.metric("Error %", f"{api_metrics_data.get('error_percentage', 0):.2f}%")
        
        # Performance metrics row
        col4, col5, col6 = st.columns(3)
        col4.metric("Avg Latency", f"{api_metrics_data.get('avg_latency', 0):.4f}s")
        col5.metric("Avg Payload", f"{api_metrics_data.get('avg_payload_size', 0):.2f} bytes")
        col6.metric("RPM", api_metrics_data.get('rpm', 0))
        
        # Enhanced Status Code Visualization
        st.subheader("Status Code Analysis")
        if api_metrics_data.get('status_codes'):
            status_df = pd.DataFrame.from_dict(
                api_metrics_data['status_codes'],
                orient='index',
                columns=['Count']
            ).sort_index()
            
            # Add color coding
            def status_color(val):
                if str(val).startswith('2'): return 'color: green'
                elif str(val).startswith('4'): return 'color: orange'
                else: return 'color: red'
            
            # Display as styled table
            st.dataframe(
                status_df.style.applymap(status_color),
                use_container_width=True
            )
            
            # Add bar chart
            st.bar_chart(status_df)
        else:
            st.warning("No status code data collected yet")

# Initialize variables
questions = None

# File uploader with session state key management
if 'file_uploader_key' not in st.session_state:
    st.session_state.file_uploader_key = 0
    
uploaded_file = st.file_uploader("Upload input file", 
                               type=["txt", "csv", "xlsx"],
                               key=f"file_uploader_{st.session_state.file_uploader_key}")

if uploaded_file:
    file_type = uploaded_file.name.split('.')[-1].lower()
    column_name = None
    if file_type in ['csv', 'xlsx']:
        # Use a unique key for the text input
        column_name = st.text_input("Enter the column name containing questions", value="question", key="column_name_input")

    try:
        # Attempt to load questions
        questions = load_questions(uploaded_file, file_type, column_name)

        if not questions:
             # Display warning only if loading succeeded but returned no questions
             st.warning("No questions loaded - check file format, content, and column name (if applicable).")

    except Exception as e:
        # Display error if loading itself failed
        st.error(f"Error loading file: {str(e)}")
        questions = None # Ensure questions is None if loading failed

# --- Display Processing Controls and Status ---
# This section now runs regardless of upload success, but buttons are active only if questions exist

if questions:
    st.success(f"Loaded {len(questions)} questions successfully.")

    # --- Processing Buttons ---
    col_start, col_stop = st.columns(2)

    with col_start:
        # Disable button if already running
        start_disabled = st.session_state.metrics.get('processing_running', False)
        if st.button("Start Processing", key="start_processing_button", disabled=start_disabled):
            # Ensure api_configs are loaded from session state
            api_configs = st.session_state.get('api_configs', [])
            if not api_configs:
                st.warning("No API configurations found. Please configure APIs on the Configuration page.")
            else:
                # Reset metrics and set state for a new run
                st.session_state.metrics['processing_running'] = True
                st.session_state.metrics['stop_processing'] = False
                st.session_state.metrics['start_time'] = time.time()
                st.session_state.metrics['end_time'] = None # Reset end time
                st.session_state.metrics['total_questions'] = len(questions)
                st.session_state.metrics['api_metrics'] = {} # Reset specific API metrics

                # Initialize metrics structure for this run
                for cfg in api_configs:
                    api_name = cfg.get("name", "Unnamed API")
                    st.session_state.metrics['api_metrics'][api_name] = {
                        'processed': 0,
                        'successes': 0, 
                        'errors': 0,
                        'latencies': [],
                        'payload_sizes': [],
                        'status_codes': {},
                        'timestamps': []
                    }

                # --- Start the actual processing loop ---
                st.info("Processing started...")
                progress_bar = st.progress(0)
                total_q = len(questions)

                for i, question in enumerate(questions):
                    # Check stop flag at the beginning of each question iteration
                    if st.session_state.metrics.get('stop_processing', False):
                        st.warning("Processing stopped by user.")
                        break # Exit the question loop

                    for api_config in api_configs:
                         # Check stop flag again before processing each API for a question
                        if st.session_state.metrics.get('stop_processing', False):
                            break # Exit the API config loop for this question

                        api_name = api_config.get("name", "Unnamed API")
                        try:
                            # Parse headers and payload template safely
                            headers = json.loads(api_config.get('headers', '{}') or '{}')
                            payload_template_str = api_config.get('payload', '{}') or '{}'
                            payload_template = json.loads(payload_template_str)

                            # Replace placeholder with current question/entry
                            if 'user_input' in payload_template:
                                payload_template['user_input'] = question
                            else:
                                payload_template['question_entry'] = question

                            # Prepare request
                            method = api_config.get('method', 'POST').upper()
                            url = api_config.get('url', '')
                            request_args = {
                                "headers": headers,
                                "timeout": 15,
                                "verify": not api_config.get('disable_ssl_verify', False)
                            }
                            
                            # Add certificate if configured
                            if api_config.get('auth_config', {}).get('cert_path'):
                                request_args['cert'] = api_config['auth_config']['cert_path']
                            
                            # Add auth token if available
                            if api_config.get('auth_config', {}).get('current_token'):
                                if 'headers' not in request_args:
                                    request_args['headers'] = {}
                                request_args['headers']['Authorization'] = f"Bearer {api_config['auth_config']['current_token']}"

                            # Make API call
                            start_time = time.time()
                            if method in ['POST', 'PUT', 'PATCH']:
                                request_args["json"] = payload_template
                                response = getattr(requests, method.lower())(url, **request_args)
                            elif method == 'GET':
                                request_args["params"] = payload_template
                                response = requests.get(url, **request_args)
                            elif method == 'DELETE':
                                request_args["json"] = payload_template
                                response = requests.delete(url, **request_args)
                            else:
                                raise ValueError(f"Unsupported HTTP method: {method}")

                            # Track metrics
                            api_metrics = st.session_state.metrics['api_metrics'][api_name]
                            is_success = 200 <= response.status_code < 300
                            
                            if is_success:
                                api_metrics['successes'] += 1
                            else:
                                api_metrics['errors'] += 1
                            
                            # Only raise for status if we want to stop on errors
                            # response.raise_for_status()  # Removed to continue processing

                            # Update metrics
                            processing_time = time.time() - start_time
                            api_metrics['processed'] += 1
                            api_metrics.setdefault('latencies', []).append(processing_time)
                            api_metrics.setdefault('payload_sizes', []).append(len(str(response.content)))
                            api_metrics.setdefault('status_codes', {})[str(response.status_code)] = api_metrics['status_codes'].get(str(response.status_code), 0) + 1
                            api_metrics.setdefault('timestamps', []).append(time.time())
                            api_metrics['rpm'] = len([t for t in api_metrics['timestamps'] if time.time() - t <= 60])

                            # Log the call
                            write_api_log(
                                api_name,
                                {
                                    "headers": headers,
                                    "payload": payload_template,
                                    "url": url,
                                    "method": method,
                                    "start_time": start_time
                                },
                                {
                                    "status_code": response.status_code,
                                    "headers": dict(response.headers),
                                    "body": response.json() if response.content else {},
                                    "processing_time": processing_time
                                }
                            )

                            write_api_metrics(api_name, api_metrics)

                        except json.JSONDecodeError as json_err:
                            st.session_state.metrics['api_metrics'][api_name]['errors'] += 1
                            logging.error(f"JSON Error for API '{api_name}': {json_err}")
                        except requests.exceptions.RequestException as req_err:
                            st.session_state.metrics['api_metrics'][api_name]['errors'] += 1
                            logging.error(f"Request Error for API '{api_name}': {req_err}")
                        except Exception as e:
                            st.session_state.metrics['api_metrics'][api_name]['errors'] += 1
                            logging.error(f"Error processing API '{api_name}': {e}")

                    # Update progress bar after processing all APIs for one question
                    progress_bar.progress((i + 1) / total_q)

                    # Check stop flag again after processing all APIs for a question
                    if st.session_state.metrics.get('stop_processing', False):
                        break # Exit the question loop

                # --- End of processing loop ---
                st.session_state.metrics['end_time'] = time.time()
                st.session_state.metrics['processing_running'] = False
                if not st.session_state.metrics.get('stop_processing', False):
                    # Save metrics for each API
                    for api_name, api_metrics in st.session_state.metrics['api_metrics'].items():
                        write_api_metrics(api_name, api_metrics)
                    output_file = "metrics_saved"  # Confirmation message
                    st.success(f"Processing finished! Results saved to {output_file}")
                st.rerun() # Rerun to update metrics display and button states

    with col_stop:
        # Disable button if not running
        stop_disabled = not st.session_state.metrics.get('processing_running', False)
        if st.button("Stop Processing", key="stop_processing_button", disabled=stop_disabled):
            st.session_state.metrics['stop_processing'] = True
            st.warning("Stop signal sent. Processing will halt soon...")
            # No rerun here, let the loop handle stopping and rerun

# --- Display Metrics ---
# Moved display_metrics call outside the 'if uploaded_file' block
# so metrics are always visible if they exist
display_metrics()

# --- Auto-refresh Section ---
# Auto-refresh only if processing is actively running
if st.session_state.metrics.get('processing_running', False):
    time.sleep(3) # Slightly shorter refresh
    st.rerun()
