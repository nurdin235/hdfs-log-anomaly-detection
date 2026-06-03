# ── app.py ────────────────────────────────────────────────────
# Live Streamlit Dashboard for HDFS Anomaly Detection System

import streamlit as st
import pandas as pd
import os
import sys
import time
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from pipeline import predict
from alerting import save_alerts, get_alerts_summary

# ── PAGE CONFIG ───────────────────────────────────────────────
st.set_page_config(
    page_title="HDFS Anomaly Detection System",
    page_icon="🚨",
    layout="wide"
)

# ── CUSTOM STYLE ──────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0a0a0a; }
    .stMetric { background: #1a1a1a; padding: 15px; border-radius: 8px; border-left: 3px solid #CC0000; }
    .alert-critical { background: #2d0000; border-left: 4px solid #CC0000; padding: 10px; border-radius: 4px; margin: 5px 0; }
    .alert-normal   { background: #002d00; border-left: 4px solid #00CC00; padding: 10px; border-radius: 4px; margin: 5px 0; }
    header { background: #000000 !important; }
</style>
""", unsafe_allow_html=True)

# ── HEADER ────────────────────────────────────────────────────
st.markdown("## 🔴 HDFS Log Anomaly Detection System")
st.markdown("**Center for Cybersecurity and Mathematical Cryptology — University of Bamenda**")
st.markdown("---")

# ── SIDEBAR ───────────────────────────────────────────────────
st.sidebar.image("https://via.placeholder.com/200x80/CC0000/FFFFFF?text=UBa+System", width=200)
st.sidebar.markdown("### System Status")
st.sidebar.success("✅ Model Loaded")
st.sidebar.success("✅ Watcher Ready")
st.sidebar.markdown("---")
st.sidebar.markdown("### Navigation")
page = st.sidebar.radio("", ["Dashboard", "Upload & Analyse", "Alerts Log", "Model Info"])

# ── PATHS ─────────────────────────────────────────────────────
BASE         = os.path.join(os.path.dirname(__file__), '..')
ALERTS_PATH  = os.path.join(BASE, 'alerts',  'alerts_log.csv')
WATCH_FOLDER = os.path.join(BASE, 'watch_folder')

# ══════════════════════════════════════════════════════════════
# PAGE 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════
if page == "Dashboard":

    st.markdown("### System Overview")

    # Metric cards
    col1, col2, col3, col4 = st.columns(4)

    alerts_data = get_alerts_summary()

    if alerts_data:
        summary, df = alerts_data
        col1.metric("Total Alerts",    summary['total_alerts'])
        col2.metric("Critical",        summary['critical'],  delta="HIGH RISK",  delta_color="inverse")
        col3.metric("Files Processed", summary['files_processed'])
        col4.metric("Latest Alert",    summary['latest_alert'])
    else:
        col1.metric("Total Alerts",    "0")
        col2.metric("Critical",        "0")
        col3.metric("Files Processed", "0")
        col4.metric("System Status",   "Watching...")

    st.markdown("---")

    # Alerts chart
    if alerts_data:
        summary, df = alerts_data
        st.markdown("### Alert Severity Distribution")

        col1, col2 = st.columns(2)

        with col1:
            severity_counts = df['Severity'].value_counts()
            fig, ax = plt.subplots(figsize=(5, 4))
            colors = ['#CC0000', '#FF6600', '#FFAA00']
            ax.bar(severity_counts.index, severity_counts.values, color=colors)
            ax.set_title("Alerts by Severity")
            ax.set_ylabel("Count")
            st.pyplot(fig)
            plt.close()

        with col2:
            st.markdown("### Recent Alerts")
            recent = df.tail(10)[['BlockId','Severity','Confidence','Timestamp']]
            st.dataframe(recent, use_container_width=True)
    else:
        st.info("No alerts yet. Upload a log file to begin analysis.")

    # Auto refresh
    st.markdown("---")
    if st.button("🔄 Refresh Dashboard"):
        st.rerun()

# ══════════════════════════════════════════════════════════════
# PAGE 2 — UPLOAD & ANALYSE
# ══════════════════════════════════════════════════════════════
elif page == "Upload & Analyse":

    st.markdown("### Upload Log File for Analysis")
    st.info("Upload an HDFS structured CSV log file. The system will automatically analyse it and raise alerts.")

    uploaded_file = st.file_uploader(
        "Drop your HDFS log file here",
        type=['csv', 'log'],
        help="Must be a structured CSV with EventId and BlockId columns"
    )

    if uploaded_file:
        st.success(f"✅ File received: {uploaded_file.name}")

        # Save to watch folder
        save_path = os.path.join(WATCH_FOLDER, uploaded_file.name)
        with open(save_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())

        if st.button("🚀 Run Analysis Now"):
            with st.spinner("Analysing log file... please wait"):

                try:
                    # Run prediction
                    results = predict(save_path)

                    # Save alerts
                    alert_count = save_alerts(results)

                    # Show results
                    total     = len(results)
                    anomalies = (results['Prediction'] == 'Anomaly').sum()
                    normals   = total - anomalies

                    st.markdown("---")
                    st.markdown("### Analysis Results")

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Sessions", total)
                    c2.metric("Normal",   normals,   delta="Safe")
                    c3.metric("Anomalies", anomalies, delta="ALERT",
                              delta_color="inverse")

                    # Show anomalies
                    if anomalies > 0:
                        st.error(f"🚨 {anomalies} anomalous sessions detected!")
                        st.markdown("#### Anomalous Sessions")
                        anom_df = results[results['Prediction'] == 'Anomaly']
                        st.dataframe(anom_df, use_container_width=True)
                    else:
                        st.success("✅ No anomalies detected. All sessions are normal.")

                    # Full results
                    st.markdown("#### Full Results")
                    st.dataframe(results, use_container_width=True)

                    # Download button
                    csv = results.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Results as CSV",
                        data=csv,
                        file_name=f"results_{uploaded_file.name}",
                        mime='text/csv'
                    )

                except Exception as e:
                    st.error(f"❌ Error during analysis: {e}")

# ══════════════════════════════════════════════════════════════
# PAGE 3 — ALERTS LOG
# ══════════════════════════════════════════════════════════════
elif page == "Alerts Log":

    st.markdown("### Full Alerts Log")

    if os.path.exists(ALERTS_PATH):
        df = pd.read_csv(ALERTS_PATH)

        # Filters
        col1, col2 = st.columns(2)
        severity_filter = col1.selectbox("Filter by Severity",
                          ["All", "CRITICAL", "HIGH", "MEDIUM"])
        file_filter = col2.selectbox("Filter by File",
                      ["All"] + df['Source_File'].unique().tolist())

        if severity_filter != "All":
            df = df[df['Severity'] == severity_filter]
        if file_filter != "All":
            df = df[df['Source_File'] == file_filter]

        st.markdown(f"Showing **{len(df)}** alerts")
        st.dataframe(df, use_container_width=True)

        # Download
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Alerts Log",
            data=csv,
            file_name="alerts_log.csv",
            mime='text/csv'
        )
    else:
        st.info("No alerts logged yet. Run an analysis first.")

# ══════════════════════════════════════════════════════════════
# PAGE 4 — MODEL INFO
# ══════════════════════════════════════════════════════════════
elif page == "Model Info":

    st.markdown("### Model Information")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Random Forest (Primary Model)")
        st.markdown("""
        | Property | Value |
        |---|---|
        | Algorithm | Random Forest Classifier |
        | Trees | 100 |
        | Features | 29 (E1 - E29) |
        | Training samples | 781,510 (after SMOTE) |
        | Accuracy | 99.99% |
        | F1-Score | 0.9981 |
        | Precision | 1.00 |
        | Recall | 1.00 |
        | Attacks caught | 5,047 / 5,051 |
        | False alarms | 15 |
        """)

    with col2:
        st.markdown("#### Isolation Forest (Baseline Model)")
        st.markdown("""
        | Property | Value |
        |---|---|
        | Algorithm | Isolation Forest |
        | Trees | 100 |
        | Features | 29 (E1 - E29) |
        | Type | Unsupervised |
        | Accuracy | 98.22% |
        | F1-Score | 0.6590 |
        | Precision | 0.75 |
        | Recall | 0.59 |
        | Attacks caught | 2,962 / 5,051 |
        | False alarms | 977 |
        """)

    st.markdown("---")
    st.markdown("#### Dataset")
    st.markdown("""
    | Property | Value |
    |---|---|
    | Source | LogHub — HDFS v1 |
    | Total sessions | 575,061 |
    | Normal sessions | 558,223 (97.1%) |
    | Anomaly sessions | 16,838 (2.9%) |
    | Features | Event count vectors E1-E29 |
    | SMOTE applied | Yes — training set only |
    """)

    # Show feature importance chart
    st.markdown("#### Feature Importance")
    img_path = os.path.join(BASE, 'feature_importance.png')
    if os.path.exists(img_path):
        st.image(img_path, use_column_width=True)