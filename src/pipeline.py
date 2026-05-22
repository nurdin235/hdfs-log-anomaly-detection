# ── pipeline.py ───────────────────────────────────────────────
import pandas as pd
import numpy as np
import joblib
import os
import re
from datetime import datetime

MODEL_PATH    = os.path.join(os.path.dirname(__file__), '..', 'model', 'rf_model.pkl')
FEATURES_PATH = os.path.join(os.path.dirname(__file__), '..', 'model', 'feature_cols.pkl')

rf_model     = joblib.load(MODEL_PATH)
feature_cols = joblib.load(FEATURES_PATH)

def extract_block_id(content):
    """Extract BlockId from log content string"""
    match = re.search(r'blk_-?\d+', str(content))
    return match.group(0) if match else None


def extract_features(log_file_path):
    """
    Reads a structured CSV log file and extracts
    event count features for each session (BlockId)
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Reading: {log_file_path}")
    df = pd.read_csv(log_file_path)
    print(f"  → Loaded {len(df)} log lines")

    # Case 1 — Already a feature matrix (has E1..E29 columns)
    if all(col in df.columns for col in feature_cols):
        print("  → Feature matrix detected directly")
        X = df[feature_cols].fillna(0)
        block_ids = df['BlockId'] if 'BlockId' in df.columns \
                    else pd.Series(range(len(df)))
        return X, block_ids

    # Case 2 — Structured log with EventId and Content columns
    if 'EventId' not in df.columns:
        raise ValueError("Log file must have an 'EventId' column")

    # Extract BlockId from Content column if not present
    if 'BlockId' not in df.columns:
        print("  → Extracting BlockId from Content column...")
        df['BlockId'] = df['Content'].apply(extract_block_id)
        before = len(df)
        df = df[df['BlockId'].notna()].copy()
        print(f"  → Found {df['BlockId'].nunique()} unique Block IDs "
              f"({before - len(df)} lines skipped — no Block ID)")

    # Build event count matrix per BlockId session
    print("  → Building event count matrix...")
    pivot = df.groupby(['BlockId', 'EventId']).size().unstack(fill_value=0)

    # Ensure all training feature columns exist — fill missing with 0
    for col in feature_cols:
        if col not in pivot.columns:
            pivot[col] = 0

    # Select only the training feature columns in correct order
    X         = pivot[feature_cols].fillna(0)
    block_ids = pivot.index

    print(f"  → Sessions extracted : {len(X)}")
    print(f"  → Features aligned   : {X.shape[1]}")
    print(f"  → Feature sample     : {dict(X.iloc[0][X.iloc[0]>0].head(5))}")

    return X, block_ids


def predict(log_file_path):
    """
    Main prediction function.
    Takes a log file path → returns DataFrame of results
    """
    X, block_ids = extract_features(log_file_path)

    predictions   = rf_model.predict(X)
    probabilities = rf_model.predict_proba(X)[:, 1]

    results = pd.DataFrame({
        'BlockId'    : block_ids,
        'Prediction' : ['Anomaly' if p == 1 else 'Normal'
                        for p in predictions],
        'Confidence' : (probabilities * 100).round(2),
        'Timestamp'  : datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Source_File': os.path.basename(log_file_path)
    })

    total     = len(results)
    anomalies = (results['Prediction'] == 'Anomaly').sum()
    normals   = total - anomalies

    print(f"  → Total sessions : {total}")
    print(f"  → Normal         : {normals}")
    print(f"  → Anomalies      : {anomalies}")

    return results