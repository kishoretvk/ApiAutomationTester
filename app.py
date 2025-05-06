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

# Enhanced Visualization Section
st.divider()
st.subheader("📊 API Performance Dashboard")

# Load and process metrics data
@st.cache_data
def load_enhanced_metrics():
    metrics_dir = Path("output/metrics")
    all_data = []

    metrics_files = sorted(metrics_dir.glob("*.json"), key=os.path.getmtime, reverse=True) # Sort by modified

    for metrics_file in metrics_files:
        try:
            with open(metrics_file) as f:
                data = json.load(f)
                # Calculate additional metrics
                data['success_rate'] = data.get('processed', 1) / max(1, data.get('processed', 1) + data.get('errors', 0))
                data['error_rate'] = data.get('errors', 0) / max(1, data.get('processed', 1) + data.get('errors', 0))
                data['api_name'] = metrics_file.stem.replace('_metrics', '')
                all_data.append(data)
        except Exception as e:
            st.error(f"Error loading {metrics_file}: {str(e)}")

    return pd.DataFrame(all_data)

if st.toggle("Show Enhanced Visualizations", value=True):
    try:
        df = load_enhanced_metrics()

        if not df.empty:
            # Dashboard Layout
            tab1, tab2, tab3 = st.tabs(["Overview", "Performance", "Status Codes"])

            with tab1:
                # Key Metrics Cards
                cols = st.columns(3)
                with cols[0]:
                    st.metric("Total APIs", len(df))
                with cols[1]:
                    st.metric("Total Requests", df['processed'].sum())
                with cols[2]:
                    st.metric("Success Rate", f"{df['success_rate'].mean()*100:.1f}%")

                # API Comparison
                st.subheader("API Comparison")
                comp_cols = st.columns(2)
                with comp_cols[0]:
                    st.bar_chart(df.set_index('api_name')[['processed', 'errors']],
                                color=['#4CAF50', '#F44336'])
                with comp_cols[1]:
                    st.bar_chart(df.set_index('api_name')[['avg_latency']],
                                color=['#2196F3'])

            with tab2:
                # Performance Trends
                st.subheader("Performance Trends")
                time_df = df.explode('timestamps')
                time_df['timestamp'] = pd.to_datetime(time_df['timestamps'], unit='s')
                
                # Enhanced Latency Analysis
                st.write("### Latency Performance (Per API)")
                
                # Calculate min, max, mean latency per API
                latency_stats = df.explode('latencies').groupby('api_name')['latencies'].agg(
                    ['min', 'max', 'mean']
                ).reset_index()
                latency_stats.columns = ['API', 'Fastest', 'Slowest', 'Average']
                
                # Display as bar chart with error bars
                st.bar_chart(
                    latency_stats.set_index('API'),
                    use_container_width=True,
                    height=400
                )
                
                # Display as formatted table
                st.write("#### Detailed Latency Metrics (seconds)")
                st.dataframe(
                    latency_stats.style.format({
                        'Fastest': '{:.3f}',
                        'Slowest': '{:.3f}', 
                        'Average': '{:.3f}'
                    }),
                    use_container_width=True,
                    hide_index=True
                )

                # Per-API RPM comparison
                st.write("### Throughput (Requests Per Minute)")
                rpm_df = df[['api_name', 'rpm']].set_index('api_name')
                st.bar_chart(
                    rpm_df,
                    use_container_width=True,
                    height=300
                )

            with tab3:
                # Enhanced Status Code Visualization
                st.subheader("Status Code Analysis")
                
                # Per-API status code distribution
                st.write("### Status Code Distribution (Per API)")
                status_df = pd.json_normalize(df['status_codes']).fillna(0)
                st.bar_chart(
                    status_df.T,
                    use_container_width=True,
                    height=500
                )

                # Detailed Metrics Table
                st.write("### API Performance Metrics")
                metrics_cols = [
                    'api_name', 'processed', 'errors', 'success_rate',
                    'avg_latency', 'rpm'
                ]
                metrics_df = df[metrics_cols].copy()
                metrics_df['success_rate'] = metrics_df['success_rate'].apply(lambda x: f"{x*100:.1f}%")
                metrics_df['avg_latency'] = metrics_df['avg_latency'].apply(lambda x: f"{x:.3f}s")
                
                # Apply color formatting
                def color_metrics(val):
                    if val == 'errors':
                        return 'color: #F44336'
                    elif val == 'success_rate':
                        return 'color: #4CAF50'
                    return None
                
                st.markdown("""
                <style>
                    .metrics-table {
                        font-size: 16px !important;
                    }
                    .metrics-table th {
                        font-weight: bold !important;
                        background-color: #f0f2f6 !important;
                    }
                    .metrics-table td {
                        padding: 8px 12px !important;
                    }
                </style>
                """, unsafe_allow_html=True)
                
                st.dataframe(
                    metrics_df.style
                        .applymap(color_metrics)
                        .set_properties(**{
                            'font-size': '16px',
                            'text-align': 'center'
                        }),
                    use_container_width=True,
                    hide_index=True
                )

        else:
            st.warning("No metrics data found. Run some API tests first.")

    except Exception as e:
        st.error(f"Error generating visualizations: {str(e)}")

# Keep existing content below
