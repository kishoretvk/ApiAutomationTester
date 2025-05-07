import streamlit as st
from streamlit_server_state import server_state, server_state_lock
import requests
import json
import time
import logging
import os
try:
    from jsonpath_ng import parse
except ImportError:
    st.error("jsonpath-ng package not found. Please install it with: pip install jsonpath-ng")

# Default headers configuration
DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

st.set_page_config(layout="wide")
st.title("API Configuration")

# Settings Sidebar
st.sidebar.subheader("Global Settings")
global_rate_limit_rate = st.sidebar.number_input("Global Rate Limit Rate (requests)", min_value=1, value=15)
global_rate_limit_period = st.sidebar.number_input("Global Rate Limit Period (seconds)", min_value=1, value=60)

# Initialize API configurations
if 'api_configs' not in st.session_state:
    st.session_state.api_configs = []
if 'api_configs' not in server_state:
    server_state.api_configs = []

# Button to add new API configuration
if st.button("Add API Configuration"):
    new_api_config = {
        "name": f"API {len(st.session_state.api_configs) + 1}",
        "url": "",
        "method": "POST",
        "payload_key": "user_input",  # Default key for text entries
        "headers": json.dumps({**DEFAULT_HEADERS}),  # Start with default headers
        "payload": '{\n  "user_input": ""\n}',  # Template with payload_key
        "disable_ssl_verify": False,
        "auth_config": {
            "auth_url": "",
            "auth_method": "POST",
            "auth_headers": json.dumps({**DEFAULT_HEADERS}),
            "auth_payload": "",
            "token_path": "token",
            "current_token": "",
            "cert_path": ""
        }
    }
    st.session_state.api_configs.append(new_api_config)
    server_state.api_configs = st.session_state.api_configs.copy()
    st.rerun()

# Display and edit API configurations
for i, api_config in enumerate(st.session_state.api_configs[:]):
    with st.expander(f"API Configuration: {api_config['name']}", expanded=True):
        api_config['name'] = st.text_input("API Name", value=api_config['name'], key=f"api_name_{i}")
        api_config['url'] = st.text_input("API URL", value=api_config['url'], key=f"api_url_{i}")
        
        method_options = ["POST", "GET", "PUT", "DELETE", "PATCH"]
        current_method = api_config.get('method', 'POST')
        api_config['method'] = st.selectbox("HTTP Method", method_options, 
                                          index=method_options.index(current_method), 
                                          key=f"api_method_{i}")
        
        api_config['payload_key'] = st.text_input("Payload Key for Text Entries", 
                                                value=api_config.get('payload_key', 'user_input'),
                                                key=f"payload_key_{i}")
        
        # Headers editor with default headers
        headers = json.loads(api_config.get('headers', '{}'))
        st.write("Headers (JSON):")
        api_config['headers'] = st.text_area("", 
                                           value=json.dumps({**DEFAULT_HEADERS, **headers}, indent=2),
                                           key=f"api_headers_{i}")
        
        # Payload template editor
        st.write("Payload Template (JSON):")
        api_config['payload'] = st.text_area("", 
                                           value=api_config.get('payload', '{\n  "user_input": ""\n}'),
                                           key=f"api_payload_{i}")
        
        # SSL Verification
        api_config['disable_ssl_verify'] = st.checkbox(
            "Disable SSL Verification", 
            value=api_config.get('disable_ssl_verify', False),
            key=f"disable_ssl_{i}"
        )
        if api_config['disable_ssl_verify']:
            st.warning("Warning: SSL verification is disabled - this is less secure!")

        # Authorization Configuration Section
        st.subheader("Authorization Settings")
        auth_config = api_config['auth_config']
        auth_config['auth_url'] = st.text_input("Auth Endpoint URL", 
            value=auth_config.get('auth_url', ''),
            key=f"auth_url_{i}")
        auth_config['auth_method'] = st.selectbox("Auth Method",
            options=["POST", "GET"],
            index=0 if auth_config.get('auth_method') == "POST" else 1,
            key=f"auth_method_{i}")
        auth_config['auth_headers'] = st.text_area("Auth Headers (JSON)",
            value=auth_config.get('auth_headers', '{}'),
            key=f"auth_headers_{i}")
        auth_config['auth_payload'] = st.text_area("Auth Payload Template",
            value=auth_config.get('auth_payload', '{\n  "username": "",\n  "password": ""\n}'),
            key=f"auth_payload_{i}")
        auth_config['token_path'] = st.text_input("Token JSON Path",
            value=auth_config.get('token_path', 'token'),
            key=f"token_path_{i}")
        
        # Certificate Upload for Auth
        cert_file = st.file_uploader("Upload Auth Certificate",
            type=['pem', 'crt', 'cert', 'key'],
            key=f"auth_cert_upload_{i}")
        if cert_file:
            cert_path = f"certs/{api_config['name']}_auth_{cert_file.name}"
            os.makedirs("certs", exist_ok=True)
            with open(cert_path, "wb") as f:
                f.write(cert_file.getbuffer())
            auth_config['cert_path'] = cert_path

        # Certificate Upload for Main API
        api_cert_file = st.file_uploader("Upload API Certificate", 
            type=['pem', 'crt', 'cert', 'key'],
            key=f"api_cert_upload_{i}")
        if api_cert_file:
            cert_path = f"certs/{api_config['name']}_api_{api_cert_file.name}"
            os.makedirs("certs", exist_ok=True)
            with open(cert_path, "wb") as f:
                f.write(api_cert_file.getbuffer())
            api_config['cert_path'] = cert_path

        # Test API Button
        if st.button("Test API Configuration", key=f"test_api_{i}"):
            try:
                headers = json.loads(api_config.get('headers', '{}'))
                payload = json.loads(api_config.get('payload', '{}'))
                cert = api_config.get('cert_path')
                
                response = requests.request(
                    method=api_config.get('method', 'POST'),
                    url=api_config.get('url', ''),
                    headers=headers,
                    json=payload,
                    cert=cert,
                    verify=not api_config.get('disable_ssl_verify', False)
                )
                response.raise_for_status()
                st.success(f"API test successful: {response.status_code}")
                st.json(response.json())
            except Exception as e:
                st.error(f"API test failed: {str(e)}")

        if st.button("Get Authorization Token", key=f"get_token_{i}"):
            try:
                headers = json.loads(auth_config['auth_headers'])
                payload = json.loads(auth_config['auth_payload'])
                cert = auth_config.get('cert_path')
                
                response = requests.request(
                    method=auth_config['auth_method'],
                    url=auth_config['auth_url'],
                    headers=headers,
                    json=payload,
                    cert=cert,
                    verify=not api_config['disable_ssl_verify']
                )
                response.raise_for_status()
                
                # Extract token using JSON path
                jsonpath_expr = parse(auth_config['token_path'])
                matches = [match.value for match in jsonpath_expr.find(response.json())]
                if not matches:
                    raise ValueError(f"Token path '{auth_config['token_path']}' not found in response")
                token = matches[0]
                auth_config['current_token'] = token
                st.success(f"Token acquired: {token[:50]}...")
                st.code(token)  # Display full token in copyable format
                
            except Exception as e:
                st.error(f"Failed to get token: {str(e)}")

        # Remove API button
        if st.button("Remove this API", key=f"remove_api_{i}"):
            st.session_state.api_configs.pop(i)
            server_state.api_configs = st.session_state.api_configs.copy()
            st.rerun()

        # Update session and server state
        st.session_state.api_configs[i] = api_config
        server_state.api_configs[i] = api_config

# [Rest of the existing file content...]
