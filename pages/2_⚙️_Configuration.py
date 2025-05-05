import streamlit as st
from streamlit_server_state import server_state, server_state_lock # Import server_state

st.title("API Configuration")

# Settings Sidebar (moved from app.py)
st.sidebar.subheader("Global Settings")
global_rate_limit_rate = st.sidebar.number_input("Global Rate Limit Rate (requests)", min_value=1, value=15)
global_rate_limit_period = st.sidebar.number_input("Global Rate Limit Period (seconds)", min_value=1, value=60)

# Initialize API configurations and global settings in session state and server state
if 'api_configs' not in st.session_state:
    st.session_state.api_configs = []
if 'api_configs' not in server_state:
    server_state.api_configs = []

if 'global_rate_limit_rate' not in st.session_state:
    st.session_state.global_rate_limit_rate = 15
if 'global_rate_limit_rate' not in server_state:
    server_state.global_rate_limit_rate = 15

if 'global_rate_limit_period' not in st.session_state:
    st.session_state.global_rate_limit_period = 60
if 'global_rate_limit_period' not in server_state:
    server_state.global_rate_limit_period = 60


st.subheader("API Configurations")

# Button to add a new API configuration
if st.button("Add API Configuration"):
    new_api_config = {
        "name": f"API {len(st.session_state.api_configs) + 1}",
        "url": "",
        "method": "POST",
        "headers": "{}", # Default empty JSON object
        "payload": ""
    }
    st.session_state.api_configs.append(new_api_config)
    server_state.api_configs = st.session_state.api_configs.copy()

# Display and edit existing API configurations
for i, api_config in enumerate(st.session_state.api_configs):
    with st.expander(f"API Configuration: {api_config['name']}"):
        api_config['name'] = st.text_input("API Name", value=api_config['name'], key=f"api_name_{i}")
        api_config['url'] = st.text_input("API URL", value=api_config['url'], key=f"api_url_{i}")
        api_config['method'] = st.selectbox("HTTP Method", ["POST", "GET", "PUT", "DELETE", "PATCH"], index=["POST", "GET", "PUT", "DELETE", "PATCH"].index(api_config['method']), key=f"api_method_{i}")
        api_config['headers'] = st.text_area("Headers (JSON)", value=api_config['headers'], key=f"api_headers_{i}")
        api_config['payload'] = st.text_area("Payload Template", value=api_config['payload'], key=f"api_payload_{i}")
        # TODO: Add certificate upload field later

        if st.button("Remove this API", key=f"remove_api_{i}"):
            st.session_state.api_configs.pop(i)
            server_state.api_configs = st.session_state.api_configs.copy()
            st.experimental_rerun() # Rerun to update the list

# Update global rate limit in server state when input changes
if st.session_state.global_rate_limit_rate != global_rate_limit_rate:
    st.session_state.global_rate_limit_rate = global_rate_limit_rate
    server_state.global_rate_limit_rate = global_rate_limit_rate

if st.session_state.global_rate_limit_period != global_rate_limit_period:
    st.session_state.global_rate_limit_period = global_rate_limit_period
    server_state.global_rate_limit_period = global_rate_limit_period
