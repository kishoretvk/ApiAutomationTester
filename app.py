import streamlit as st
import json
import os
import time
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="API Processor App", 
    layout="wide"
)

# ... (keep existing imports and setup code) ...

# Add new visualization section at the bottom
st.divider()
st.subheader("API Performance Visualizations")

# Load all metrics data
@st.cache_data
def load_all_metrics():
    metrics_dir = Path("output/metrics")
    all_metrics = []
    
    for metrics_file in metrics_dir.glob("*.json"):
        try:
            with open(metrics_file) as f:
                data = json.load(f)
                data['api_name'] = metrics_file.stem.replace('_metrics', '')
                all_metrics.append(data)
        except Exception as e:
            st.error(f"Error loading {metrics_file}: {str(e)}")
    
    return pd.DataFrame(all_metrics)

if st.button("Load Visualization Data"):
    try:
        df = load_all_metrics()
        
        if not df.empty:
            # Performance Trends Chart
            st.write("### API Performance Over Time")
            time_df = df.explode('timestamps')
            time_df['timestamp'] = pd.to_datetime(time_df['timestamps'], unit='s')
            st.line_chart(time_df.set_index('timestamp')[['avg_latency']], 
                         use_container_width=True)
            
            # API Comparison Chart
            st.write("### API Comparison")
            cols = st.columns(2)
            with cols[0]:
                st.bar_chart(df.set_index('api_name')[['processed', 'errors']])
            with cols[1]:
                st.bar_chart(df.set_index('api_name')[['avg_latency']])
            
            # Status Code Distribution
            st.write("### Status Code Distribution")
            status_df = pd.json_normalize(df['status_codes']).fillna(0)
            st.area_chart(status_df.T)
            
            # Raw Data View
            st.write("### Raw Metrics Data")
            st.dataframe(df)
        else:
            st.warning("No metrics data found. Run some API tests first.")
            
    except Exception as e:
        st.error(f"Error generating visualizations: {str(e)}")

# Keep existing content below
