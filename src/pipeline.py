# ── pipeline.py ───────────────────────────────────────────────
# Feature extraction and prediction pipeline
# Location: hdfs_project/src/pipeline.py

import pandas as pd
import numpy as np
import joblib
import os
import re
from datetime import datetime

# ── MODEL PATHS ───────────────────────────────────────────────
MODEL_PATH    = os.path.join(os.path.dirname(__file__), '..', 'model', 'rf_model.pkl')
FEATURES_PATH = os.path.join(os.path.dirname(__file__), '..', 'model', 'feature_cols.pkl')

# ── LOAD MODEL ONCE AT STARTUP ────────────────────────────────
rf_model     = joblib.load(MODEL_PATH)
feature_cols = joblib.load(FEATURES_PATH)

print(f"[pipeline] ✅ Model loaded: {MODEL_PATH}")
print(f"[pipeline] ✅ Features loaded: {len(feature_cols)} columns")


# ── HELPER FUNCTIONS ──────────────────────────────────────────

def extract_block_id(content):
    """Extract BlockId from log content string"""
    match = re.search(r'blk_-?\d+', str(content))
    return match.group(0) if match else None


def extract_features(log_file_path):
    """
    Reads a structured CSV log file and extracts
    event count features for each session (BlockId).

    Supports two input formats:
      1. Pre-computed feature matrix (has E1..E29 columns)
      2. Raw structured log with EventId and Content columns
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Reading: {log_file_path}")
    df = pd.read_csv(log_file_path)
    print(f"  → Loaded {len(df)} log lines")

    # ── Case 1: Already a feature matrix ──────────────────────
    if all(col in df.columns for col in feature_cols):
        print("  → Feature matrix detected directly")
        X = df[feature_cols].fillna(0)
        block_ids = df['BlockId'] if 'BlockId' in df.columns \
                    else pd.Series(range(len(df)))
        return X, block_ids

    # ── Case 2: Raw structured log ────────────────────────────
    if 'EventId' not in df.columns:
        raise ValueError(
            "Log file must have an 'EventId' column or pre-computed "
            "feature columns (E1-E29). Please check your file format."
        )

    # Extract BlockId from Content column if not already present
    if 'BlockId' not in df.columns:
        if 'Content' not in df.columns:
            raise ValueError(
                "Log file must have either a 'BlockId' column or a "
                "'Content' column to extract Block IDs from."
            )
        print("  → Extracting BlockId from Content column...")
        df['BlockId'] = df['Content'].apply(extract_block_id)
        before = len(df)
        df = df[df['BlockId'].notna()].copy()
        skipped = before - len(df)
        print(f"  → Found {df['BlockId'].nunique()} unique Block IDs "
              f"({skipped} lines skipped — no Block ID found)")

    # Build event count matrix per BlockId session
    print("  → Building event count matrix per session...")
    pivot = df.groupby(['BlockId', 'EventId']).size().unstack(fill_value=0)

    # Ensure all training feature columns exist — fill missing with 0
    for col in feature_cols:
        if col not in pivot.columns:
            pivot[col] = 0

    # Select only the training feature columns in the correct order
    X         = pivot[feature_cols].fillna(0)
    block_ids = pivot.index

    print(f"  → Sessions extracted : {len(X)}")
    print(f"  → Features aligned   : {X.shape[1]}")

    if len(X) > 0:
        sample = dict(X.iloc[0][X.iloc[0] > 0].head(5))
        print(f"  → Feature sample     : {sample}")

    return X, block_ids


# ── MAIN PREDICTION FUNCTION ──────────────────────────────────

def predict(log_file_path):
    """
    Main prediction function.
    Takes a log file path → returns DataFrame with results.

    Returns columns:
        BlockId     — session identifier
        Prediction  — 'Anomaly' or 'Normal'
        Confidence  — model confidence score (0–100, 2 decimal places)
        Timestamp   — time of prediction
        Source_File — name of the input file
    """
    X, block_ids = extract_features(log_file_path)

    # Get predictions and probabilities
    predictions   = rf_model.predict(X)
    probabilities = rf_model.predict_proba(X)[:, 1]  # probability of Anomaly class

    # Build results DataFrame
    results = pd.DataFrame({
        'BlockId'    : block_ids,
        'Prediction' : ['Anomaly' if p == 1 else 'Normal' for p in predictions],
        'Confidence' : (probabilities * 100).round(2),
        'Timestamp'  : datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Source_File': os.path.basename(log_file_path)
    })

    # Summary log
    total     = len(results)
    anomalies = (results['Prediction'] == 'Anomaly').sum()
    normals   = total - anomalies

    print(f"  → Total sessions  : {total}")
    print(f"  → Normal          : {normals}")
    print(f"  → Anomalies       : {anomalies}")
    print(f"  → Anomaly rate    : {(anomalies/total*100):.2f}%")

    return results