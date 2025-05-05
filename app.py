import streamlit as st
import json
import os
import time # Import time for calculating elapsed time
import pandas as pd # Import pandas for DataFrame

st.set_page_config(
    page_title="API Processor App",
    layout="wide"
)

st.title("Welcome to the API Test Automation App")

st.markdown("""
This application is a versatile tool designed to process questions or data points from various file formats (TXT, CSV, XLSX) by sending them to one or more configured external APIs. It efficiently manages API calls, respects rate limits, and provides features for resuming interrupted processing jobs.

Key Features:
- **Flexible Input:** Supports reading questions/data from `.txt`, `.csv`, and `.xlsx` files.
- **Multiple API Support:** Configure and send data to multiple API endpoints simultaneously.
- **Rate Limiting:** Manages request rates to avoid overwhelming APIs.
- **State Management:** Saves processing progress, allowing you to resume jobs from where they left off.
- **Real-time Metrics:** Displays live processing statistics, including latency, payload size, error rates, and requests per minute (RPM).
- **Configurable:** Easily set up API URLs, methods, headers, payloads, and global settings through the Configuration page.

Navigate to the pages on the left to:
- **⚙️ Configuration**: Define and manage your API endpoints, set global rate limits, and configure request timeouts and retry logic.
- **📊 Metrics**: Upload your input file, initiate or stop the processing job, and monitor detailed real-time metrics and results for each configured API.
""")

# --- Sample Processing Metrics Dashboard (Minimized) ---
SAMPLE_DATA_FILE = "sample_metrics_data.json"

sample_metrics = {}
if os.path.exists(SAMPLE_DATA_FILE):
    try:
        with open(SAMPLE_DATA_FILE, 'r') as f:
            sample_metrics = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        st.warning("Could not load sample metrics data.")

if sample_metrics:
    with st.expander("View Sample Metrics Dashboard"):
        st.subheader("Sample Processing Metrics Dashboard")
        st.info("This is a sample dashboard showing potential metrics. Run a job on the Metrics page to see live data.")

        st.metric("Total Questions (Sample)", sample_metrics.get('total_questions', 0))

        for api_name, api_metric_data in sample_metrics.get('api_metrics', {}).items():
            st.write(f"**{api_name} (Sample)**")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Processed", api_metric_data.get('processed', 0), delta=f"Skipped: {api_metric_data.get('skipped', 0)}, Errors: {api_metric_data.get('errors', 0)}")

            processed_count = api_metric_data.get('processed', 0)
            if processed_count > 0:
                col2.metric("Avg Latency", f"{api_metric_data.get('total_latency', 0) / processed_count:.4f}s")
                col3.metric("Avg Payload Size", f"{api_metric_data.get('total_payload_size', 0) / processed_count:.2f} bytes")
                error_count = api_metric_data.get('errors', 0)
                total_calls = processed_count + api_metric_data.get('skipped', 0) + error_count
                if total_calls > 0:
                     col4.metric("Error Percentage", f"{(error_count / total_calls) * 100:.2f}%")
                else:
                     col4.metric("Error Percentage", "N/A")
            else:
                col2.metric("Avg Latency", "N/A")
                col3.metric("Avg Payload Size", "N/A")
                col4.metric("Error Percentage", "N/A")

            # Add Sample RPM and Status Code Distribution
            st.write("Sample Status Code Distribution:")
            sample_status_codes = api_metric_data.get('status_codes', {})
            if sample_status_codes:
                sample_status_codes_df = pd.DataFrame(list(sample_status_codes.items()), columns=['Status Code', 'Count'])
                st.dataframe(sample_status_codes_df, use_container_width=True)
            else:
                st.write("No sample status code data available.")

            # Placeholder for Sample Graph
            st.write("Sample Graph Placeholder")
            # st.line_chart(data) # Example of adding a chart

        start_time = sample_metrics.get('start_time')
        end_time = sample_metrics.get('end_time')
        if start_time and end_time:
            st.metric("Total Processing Time (Sample)", f"{end_time - start_time:.2f}s")
        else:
            st.metric("Total Processing Time (Sample)", "N/A")
else:
     st.info("Sample metrics data file not found. Create 'streamlit_api_processor/sample_metrics_data.json' to see a sample dashboard.")


# --- Actual Processing Metrics ---
st.subheader("Current Processing Metrics")

# Access metrics from session state
metrics = st.session_state.get('metrics', {})

if metrics.get('total_questions', 0) > 0:
    st.metric("Total Questions", metrics.get('total_questions', 0))

    for api_name, api_metric_data in metrics.get('api_metrics', {}).items():
        st.write(f"**{api_name}**")
        col1, col2, col3, col4, col5 = st.columns(5) # Use 5 columns for more metrics including RPM
        col1.metric("Processed", api_metric_data.get('processed', 0), delta=f"Skipped: {api_metric_data.get('skipped', 0)}, Errors: {api_metric_data.get('errors', 0)}")

        processed_count = api_metric_data.get('processed', 0)
        if processed_count > 0:
            col2.metric("Avg Latency", f"{api_metric_data.get('total_latency', 0) / processed_count:.4f}s")
            col3.metric("Avg Payload Size", f"{api_metric_data.get('total_payload_size', 0) / processed_count:.2f} bytes")
            error_count = api_metric_data.get('errors', 0)
            total_calls = processed_count + api_metric_data.get('skipped', 0) + error_count
            if total_calls > 0:
                 col4.metric("Error Percentage", f"{(error_count / total_calls) * 100:.2f}%")
            else:
                 col4.metric("Error Percentage", "N/A")
        else:
            col2.metric("Avg Latency", "N/A")
            col3.metric("Avg Payload Size", "N/A")
            col4.metric("Error Percentage", "N/A")

        # Calculate and display Requests Per Minute (RPM)
        completion_times = api_metric_data.get('completion_times', [])
        current_time = time.monotonic()
        # Filter timestamps within the last 60 seconds
        recent_completion_times = [t for t in completion_times if current_time - t <= 60]
        rpm = (len(recent_completion_times) / 60) if recent_completion_times else 0
        col5.metric("RPM (Last 60s)", f"{rpm:.2f}")

        # Display status code distribution
        st.write("Status Code Distribution:")
        status_codes = api_metric_data.get('status_codes', {})
        if status_codes:
            status_codes_df = pd.DataFrame(list(status_codes.items()), columns=['Status Code', 'Count'])
            st.dataframe(status_codes_df, use_container_width=True)
        else:
            st.write("No status code data available.")


    start_time = metrics.get('start_time')
    end_time = metrics.get('end_time')
    if start_time and end_time:
        st.metric("Total Processing Time", f"{end_time - start_time:.2f}s")
    elif start_time:
         st.metric("Processing Time Elapsed", f"{time.monotonic() - start_time:.2f}s")
    else:
        st.metric("Total Processing Time", "N/A")

else:
    st.info("No processing metrics available yet. Configure APIs and run a job on the Metrics page.")

# You can add more introductory content or instructions here.
