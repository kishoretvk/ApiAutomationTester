import streamlit as st
from streamlit_server_state import server_state, server_state_lock # Import server_state
import requests # Import requests for making API calls
import json # Import json for parsing headers/payload
import time # Import time for potential delays
import logging # Import the logging module

st.set_page_config(layout="wide") # Ensure wide layout for better display
st.title("API Configuration")

# Configure logging (optional, but good practice if using logging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Settings Sidebar (moved from app.py)
st.sidebar.subheader("Global Settings")
global_rate_limit_rate = st.sidebar.number_input("Global Rate Limit Rate (requests)", min_value=1, value=st.session_state.get('global_rate_limit_rate', 15), key="sidebar_rate_rate")
global_rate_limit_period = st.sidebar.number_input("Global Rate Limit Period (seconds)", min_value=1, value=st.session_state.get('global_rate_limit_period', 60), key="sidebar_rate_period")

# Initialize API configurations and global settings in session state and server state
if 'api_configs' not in st.session_state:
    st.session_state.api_configs = []
if 'api_configs' not in server_state:
    server_state.api_configs = []

# Initialize session state for test results
if 'test_results' not in st.session_state:
    st.session_state.test_results = {} # Stores results like {index: {"status": ..., "body": ..., "error": ...}}
if 'test_api_index_to_run' not in st.session_state:
    st.session_state.test_api_index_to_run = None # Index of the API test to run on the next rerun

# Update global rate limit in session state and server state when input changes
# Use the keys from the sidebar inputs
if st.session_state.get('global_rate_limit_rate') != global_rate_limit_rate:
    st.session_state.global_rate_limit_rate = global_rate_limit_rate
    server_state.global_rate_limit_rate = global_rate_limit_rate

if st.session_state.get('global_rate_limit_period') != global_rate_limit_period:
    st.session_state.global_rate_limit_period = global_rate_limit_period
    server_state.global_rate_limit_period = global_rate_limit_period


st.subheader("API Configurations")

# Button to add a new API configuration
if st.button("Add API Configuration", key="add_api_button"):
    new_api_config = {
        "name": f"API {len(st.session_state.api_configs) + 1}",
        "url": "",
        "method": "POST",
        "headers": "{}", # Default empty JSON object
        "payload": "{\n  \"user_input\": \"\"\n}" # Default JSON with user_input
    }
    st.session_state.api_configs.append(new_api_config)
    server_state.api_configs = st.session_state.api_configs.copy()
    # Set the new expander to be open by default - not possible without 'key'
    # st.session_state.expander_states[len(st.session_state.api_configs) - 1] = True # Removed
    st.rerun() # Rerun to show the new configuration

# Display and edit existing API configurations
# Iterate over a copy to allow modification during iteration (e.g., removal)
api_configs_copy = st.session_state.api_configs[:]
for i, api_config in enumerate(api_configs_copy):
    # Removed 'key' parameter from expander and the logic relying on it
    # Use a simple session state flag for expanded state, defaulting to True
    expander_state_key = f"expander_expanded_{i}"
    is_expanded = st.session_state.get(expander_state_key, True)

    with st.expander(f"API Configuration: {api_config['name']}", expanded=is_expanded):
        # Update expander state in session state when user interacts - relies on Streamlit's internal key
        # This line caused the error, removing it.
        # st.session_state[f"expander_expanded_{i}"] = st.session_state[f"api_expander_{i}"] # Removed

        # Use unique keys for input widgets based on index
        api_config['name'] = st.text_input("API Name", value=api_config.get('name', f"API {i+1}"), key=f"api_name_{i}")
        api_config['url'] = st.text_input("API URL", value=api_config.get('url', ''), key=f"api_url_{i}")
        method_options = ["POST", "GET", "PUT", "DELETE", "PATCH"]
        current_method_index = method_options.index(api_config.get('method', 'POST')) if api_config.get('method', 'POST') in method_options else 0
        api_config['method'] = st.selectbox("HTTP Method", method_options, index=current_method_index, key=f"api_method_{i}")
        api_config['headers'] = st.text_area("Headers (JSON)", value=api_config.get('headers', '{}'), key=f"api_headers_{i}")
        api_config['payload'] = st.text_area("Payload Template", value=api_config.get('payload', '{\n  "user_input": ""\n}'), key=f"api_payload_{i}")
        # TODO: Add certificate upload field later

        # Update the actual api_configs list in session state and server state
        # This is important because the user might edit fields without clicking a button
        st.session_state.api_configs[i] = api_config
        server_state.api_configs[i] = api_config # Keep server state in sync

        st.subheader("Test API")
        # Add a button to test this specific API configuration
        test_button_key = f"test_api_button_{i}"
        if st.button("Test This API", key=test_button_key):
            # Set the index of the API test to run on the next rerun
            st.session_state.test_api_index_to_run = i
            # Set testing status immediately
            st.session_state.test_results[i] = {"status": "Testing...", "body": None, "error": None}
            # Ensure this expander stays open to show results - not possible with key
            # st.session_state.expander_states[i] = True # Removed
            st.session_state[expander_state_key] = True # Set the simple flag to keep it open
            st.rerun() # Trigger rerun to perform the test

        # Display test results if available for this API
        if i in st.session_state.test_results:
            result = st.session_state.test_results[i]
            if result["error"]:
                st.error(f"Test Failed: {result['error']}")
            elif result["status"] == "Testing...":
                 st.info("Test in progress...")
            else:
                st.success(f"Test Successful: Status Code {result['status']}")
                st.json(result["body"]) # Display response body as JSON

        st.divider() # Add a small separator before the remove button

        if st.button("Remove this API", key=f"remove_api_{i}"):
            # Remove from session state and server state
            st.session_state.api_configs.pop(i)
            server_state.api_configs = st.session_state.api_configs.copy()
            # Also remove test results and expander state for this API if they exist
            if i in st.session_state.test_results:
                 del st.session_state.test_results[i]
            # if i in st.session_state.expander_states: # Removed expander state management
            #      del st.session_state.expander_states[i]
            if expander_state_key in st.session_state: # Remove the simple flag
                 del st.session_state[expander_state_key]

            # Need to re-index test_results after popping
            new_test_results = {idx: result for idx, result in enumerate(st.session_state.test_results.values())}
            st.session_state.test_results = new_test_results
            # Re-indexing expander states is complex without key, will likely reset on rerun anyway

            st.rerun() # Rerun to update the list

# --- Perform the actual test API call if triggered ---
# This block runs on every rerun, but only performs the test if test_api_index_to_run is set
if st.session_state.test_api_index_to_run is not None:
    index_to_test = st.session_state.test_api_index_to_run
    # Clear the flag immediately to prevent re-running the test on subsequent reruns
    st.session_state.test_api_index_to_run = None

    # Retrieve the API config using the index (use the list from session state)
    if index_to_test < len(st.session_state.api_configs):
        current_api_config = st.session_state.api_configs[index_to_test]

        try:
            # Parse headers and payload template safely
            headers = json.loads(current_api_config.get('headers', '{}') or '{}')
            payload_template_str = current_api_config.get('payload', '{}') or '{}'
            payload_template = json.loads(payload_template_str)

            # For testing, we can use a sample value for 'user_input' or just send the template
            # Let's send the template as is for a basic connectivity test
            # If 'user_input' exists, maybe put a placeholder? Let's just send the template.

            # Make the API call dynamically based on method
            method = current_api_config.get('method', 'POST').upper()
            url = current_api_config.get('url', '')

            response = None
            request_args = {
                "headers": headers,
                "timeout": 15 # Add a timeout
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
                 # For GET, send payload items as URL params
                request_args["params"] = payload_template
                response = requests.get(url, **request_args)
            elif method == 'DELETE':
                # Send payload as json for DELETE
                request_args["json"] = payload_template
                response = requests.delete(url, **request_args)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            # Store success result
            st.session_state.test_results[index_to_test] = {
                "status": response.status_code,
                "body": response.json() if response.content else {}, # Try to parse JSON body
                "error": None
            }

        except json.JSONDecodeError as json_err:
             st.session_state.test_results[index_to_test] = {
                "status": "JSON Error",
                "body": None,
                "error": f"JSON Parsing Error: {json_err}"
            }
             logging.error(f"Test JSON Error for API '{current_api_config.get('name', 'Unnamed')}': {json_err}")
        except requests.exceptions.RequestException as req_err:
             st.session_state.test_results[index_to_test] = {
                "status": "Request Error",
                "body": None,
                "error": f"Request Failed: {req_err}"
            }
             logging.error(f"Test Request Error for API '{current_api_config.get('name', 'Unnamed')}': {req_err}")
        except Exception as e:
             st.session_state.test_results[index_to_test] = {
                "status": "Error",
                "body": None,
                "error": f"An unexpected error occurred: {e}"
            }
             logging.error(f"Test General Error for API '{current_api_config.get('name', 'Unnamed')}': {e}")

        # Trigger a final rerun to display the result
        st.rerun()
    else:
        # Handle case where index is out of bounds (shouldn't happen with proper state management)
        logging.error(f"Test API index {index_to_test} out of bounds.")
        if index_to_test in st.session_state.test_results:
             st.session_state.test_results[index_to_test] = {
                "status": "Error",
                "body": None,
                "error": "Internal error: API index out of bounds."
            }
             st.rerun()


st.divider() # Add a visual separator

if st.button("Reset All Configurations", key="reset_configs_button", type="secondary"):
    if 'api_configs' in st.session_state:
        st.session_state.api_configs = []
    if 'api_configs' in server_state:
        server_state.api_configs = []
    # Clear test results and expander states on full reset
    st.session_state.test_results = {}
    # st.session_state.expander_states = {} # Removed expander state management
    st.session_state.test_api_index_to_run = None
    # Clear simple expander flags
    keys_to_delete = [key for key in st.session_state.keys() if key.startswith("expander_expanded_")]
    for key in keys_to_delete:
        del st.session_state[key]

    st.success("All API configurations have been reset.")
    st.rerun() # Rerun to clear the display
