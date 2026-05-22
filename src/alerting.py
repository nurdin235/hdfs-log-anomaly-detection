# ── alerting.py ───────────────────────────────────────────────
# Handles alert generation when anomalies are detected

import pandas as pd
import os
from datetime import datetime

ALERTS_PATH = os.path.join(os.path.dirname(__file__), '..', 'alerts', 'alerts_log.csv')

def save_alerts(results):
    """
    Takes prediction results and saves anomalies
    to the alerts log file automatically
    """
    # Filter only anomalies
    anomalies = results[results['Prediction'] == 'Anomaly'].copy()

    if anomalies.empty:
        print(f"  → No anomalies found. No alerts raised.")
        return 0

    # Add severity level based on confidence
    anomalies['Severity'] = anomalies['Confidence'].apply(
        lambda x: 'CRITICAL' if x >= 90 else 'HIGH' if x >= 75 else 'MEDIUM'
    )

    # Append to alerts log (create if not exists)
    file_exists = os.path.exists(ALERTS_PATH)

    anomalies.to_csv(
        ALERTS_PATH,
        mode='a',
        header=not file_exists,
        index=False
    )

    # Print alert summary
    critical = (anomalies['Severity'] == 'CRITICAL').sum()
    high     = (anomalies['Severity'] == 'HIGH').sum()
    medium   = (anomalies['Severity'] == 'MEDIUM').sum()

    print(f"  → 🚨 ALERTS RAISED: {len(anomalies)} anomalies detected")
    print(f"     CRITICAL : {critical}")
    print(f"     HIGH     : {high}")
    print(f"     MEDIUM   : {medium}")
    print(f"  → Alerts saved to: alerts/alerts_log.csv")

    return len(anomalies)


def get_alerts_summary():
    """
    Returns a summary of all alerts logged so far
    """
    if not os.path.exists(ALERTS_PATH):
        return None

    df = pd.read_csv(ALERTS_PATH)

    summary = {
        'total_alerts'   : len(df),
        'critical'       : (df['Severity'] == 'CRITICAL').sum(),
        'high'           : (df['Severity'] == 'HIGH').sum(),
        'medium'         : (df['Severity'] == 'MEDIUM').sum(),
        'latest_alert'   : df['Timestamp'].max(),
        'files_processed': df['Source_File'].nunique()
    }

    return summary, df