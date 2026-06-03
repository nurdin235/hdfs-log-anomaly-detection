# ── alerting.py ───────────────────────────────────────────────
# Handles alert generation when anomalies are detected

import pandas as pd
import os
from datetime import datetime

ALERTS_PATH = os.path.join(os.path.dirname(__file__), '..', 'alerts', 'alerts_log.csv')

def save_alerts(results):
    """
    Takes prediction results and saves anomalies
    to the alerts log file automatically.

    Severity tiers (based on confidence score):
        CRITICAL : confidence >= 95  — near-certain threat
        HIGH     : confidence >= 80  — strong indicator
        MEDIUM   : confidence >= 65  — moderate suspicion
        LOW      : confidence <  65  — weak signal, review advised
    """
    # Filter only anomalies
    anomalies = results[results['Prediction'] == 'Anomaly'].copy()

    if anomalies.empty:
        print(f"  → No anomalies found. No alerts raised.")
        return 0

    # ── FIXED: Severity logic now uses 4 tiers with proper thresholds ──
    def assign_severity(confidence):
        if confidence >= 95:
            return 'CRITICAL'
        elif confidence >= 80:
            return 'HIGH'
        elif confidence >= 65:
            return 'MEDIUM'
        else:
            return 'LOW'

    anomalies['Severity'] = anomalies['Confidence'].apply(assign_severity)

    # Add timestamp if not present
    if 'Timestamp' not in anomalies.columns:
        anomalies['Timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

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
    low      = (anomalies['Severity'] == 'LOW').sum()

    print(f"  → 🚨 ALERTS RAISED: {len(anomalies)} anomalies detected")
    print(f"     CRITICAL : {critical}")
    print(f"     HIGH     : {high}")
    print(f"     MEDIUM   : {medium}")
    print(f"     LOW      : {low}")
    print(f"  → Alerts saved to: alerts/alerts_log.csv")

    return len(anomalies)


def get_alerts_summary():
    """
    Returns a summary of all alerts logged so far
    """
    if not os.path.exists(ALERTS_PATH):
        return None

    df = pd.read_csv(ALERTS_PATH)

    # ── FIXED: Summary now includes LOW severity + formatted numbers ──
    summary = {
        'total_alerts'   : len(df),
        'critical'       : int((df['Severity'] == 'CRITICAL').sum()),
        'high'           : int((df['Severity'] == 'HIGH').sum()),
        'medium'         : int((df['Severity'] == 'MEDIUM').sum()),
        'low'            : int((df['Severity'] == 'LOW').sum()),
        'latest_alert'   : df['Timestamp'].max(),
        'files_processed': int(df['Source_File'].nunique())
    }

    return summary, df