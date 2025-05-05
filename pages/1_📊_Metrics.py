import streamlit as st
import os
import pandas as pd
import time
import json
import numpy as np
import logging
import requests # Ensure requests is imported

# Assuming these imports exist and are correct
from input_handler import load_questions
# from api_client import ApiClient, RateLimiter # Commenting out as ApiClient isn't used directly in the fixed processing loop
# from state_manager import load_state, save_state, is_processed, mark_as_processed # Commenting out unused state functions
# from output_writer import write_result # Commenting out as write_result isn't used directly in the fixed processing loop

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
        col1, col2 = st.columns(2)
        col1.metric("Processed", api_metrics_data.get('processed', 0))
        col2.metric("Errors", api_metrics_data.get('errors', 0))
        # Add more detailed metrics like latency, payload size if needed later

# --- Main UI Section ---
uploaded_file = st.file_uploader("Upload input file", type=["txt", "csv", "xlsx"], key="file_uploader")

questions = None # Initialize questions to None

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
                    st.session_state.metrics['api_metrics'][api_name] = {'processed': 0, 'errors': 0}

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
                            headers = json.loads(api_config.get('headers', '{}') or '{}') # Ensure valid JSON string
                            payload_template_str = api_config.get('payload', '{}') or '{}' # Ensure valid JSON string
                            payload_template = json.loads(payload_template_str)

                            # Replace placeholder with current question/entry
                            if 'user_input' in payload_template:
                                payload_template['user_input'] = question
                            else:
                                # If 'user_input' key doesn't exist, maybe add as a default key?
                                payload_template['question_entry'] = question # Example fallback

                            # --- Make the API call dynamically based on method ---
                            method = api_config.get('method', 'POST').upper()
                            url = api_config.get('url', '')

                            response = None
                            request_args = {
                                "headers": headers,
                                "timeout": 15
                            }

                            if method in ['POST', 'PUT', 'PATCH']:
                                request_args["json"] = payload_template
                                if method == 'POST':
                                    response = requests.post(url, **request_args)
                                elif method == 'PUT':
                                    response = requests.put(url, **request_args)
                                else: # PATCH
                                    response = requests.patch(url, **request_args)
                            elif method == 'GET':
                                # For GET, data is usually sent as URL params.
                                # We'll add the payload items as params for simplicity,
                                # though this might not be standard REST practice for complex bodies.
                                request_args["params"] = payload_template
                                response = requests.get(url, **request_args)
                            elif method == 'DELETE':
                                # DELETE might have a body or not, depending on API.
                                # Sending payload as json for flexibility, though often it's param-based or no body.
                                request_args["json"] = payload_template
                                response = requests.delete(url, **request_args)
                            else:
                                # Handle unsupported methods or raise an error
                                logging.error(f"Unsupported HTTP method '{method}' for API '{api_name}'")
                                raise ValueError(f"Unsupported HTTP method: {method}")

                            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

                            # Update metrics on success
                            st.session_state.metrics['api_metrics'][api_name]['processed'] += 1
                            # TODO: Add result writing if needed: write_result(f"{api_name}_results.jsonl", response.json())

                        except json.JSONDecodeError as json_err:
                            st.session_state.metrics['api_metrics'][api_name]['errors'] += 1
                            logging.error(f"JSON Error for API '{api_name}': {json_err}. Headers: '{api_config.get('headers', '')}', Payload Template: '{payload_template_str}'")
                        except requests.exceptions.RequestException as req_err:
                            st.session_state.metrics['api_metrics'][api_name]['errors'] += 1
                            logging.error(f"Request Error for API '{api_name}' processing question '{question}': {req_err}")
                        except Exception as e:
                            st.session_state.metrics['api_metrics'][api_name]['errors'] += 1
                            logging.error(f"General Error for API '{api_name}' processing question '{question}': {e}")

                    # Update progress bar after processing all APIs for one question
                    progress_bar.progress((i + 1) / total_q)

                    # Check stop flag again after processing all APIs for a question
                    if st.session_state.metrics.get('stop_processing', False):
                        break # Exit the question loop

                # --- End of processing loop ---
                st.session_state.metrics['end_time'] = time.time()
                st.session_state.metrics['processing_running'] = False
                if not st.session_state.metrics.get('stop_processing', False):
                    st.success("Processing finished.")
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
