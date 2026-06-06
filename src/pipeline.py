"""Feature extraction and inference for HDFS anomaly detection."""

from functools import lru_cache
from pathlib import Path
from typing import BinaryIO, Union
import os
import re

import joblib
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT_DIR / "model" / "rf_model.pkl"
FEATURES_PATH = ROOT_DIR / "model" / "feature_cols.pkl"
BLOCK_PATTERN = re.compile(r"blk_-?\d+")

DataSource = Union[str, os.PathLike, BinaryIO, pd.DataFrame]


@lru_cache(maxsize=1)
def load_model_assets():
    """Load and cache model artifacts once per process or function instance."""
    model = joblib.load(MODEL_PATH)
    feature_columns = list(joblib.load(FEATURES_PATH))
    return model, feature_columns


def get_feature_columns():
    """Return the ordered feature names expected by the trained model."""
    _, feature_columns = load_model_assets()
    return feature_columns


def extract_block_id(content):
    """Extract an HDFS block identifier from a log content value."""
    match = BLOCK_PATTERN.search(str(content))
    return match.group(0) if match else None


def _read_dataframe(source: DataSource) -> pd.DataFrame:
    if isinstance(source, pd.DataFrame):
        return source.copy()

    try:
        return pd.read_csv(source)
    except UnicodeDecodeError as exc:
        raise ValueError("The uploaded file must be a UTF-8 encoded CSV.") from exc
    except pd.errors.EmptyDataError as exc:
        raise ValueError("The uploaded CSV is empty.") from exc
    except pd.errors.ParserError as exc:
        raise ValueError(f"The uploaded CSV could not be parsed: {exc}") from exc


def extract_features(source: DataSource):
    """
    Build one E1-E29 event-count vector per HDFS block session.

    Supported input formats:
    1. A feature matrix containing every trained feature column.
    2. A structured HDFS log containing EventId and either BlockId or Content.
    """
    dataframe = _read_dataframe(source)
    _, feature_columns = load_model_assets()

    if dataframe.empty:
        raise ValueError("The uploaded CSV contains headers but no data rows.")

    if all(column in dataframe.columns for column in feature_columns):
        features = (
            dataframe[feature_columns]
            .apply(pd.to_numeric, errors="coerce")
            .fillna(0)
        )
        if "BlockId" in dataframe.columns:
            block_ids = dataframe["BlockId"].fillna("unknown").astype(str)
        else:
            block_ids = pd.Series(
                (f"session_{index + 1}" for index in range(len(dataframe))),
                index=dataframe.index,
            )
        return features, block_ids

    if "EventId" not in dataframe.columns:
        raise ValueError(
            "Expected an EventId column or a feature matrix with columns E1-E29."
        )

    dataframe["EventId"] = dataframe["EventId"].astype(str).str.strip()

    if "BlockId" not in dataframe.columns:
        if "Content" not in dataframe.columns:
            raise ValueError(
                "A structured log must include BlockId or Content so sessions "
                "can be identified."
            )
        dataframe["BlockId"] = dataframe["Content"].map(extract_block_id)

    dataframe = dataframe[dataframe["BlockId"].notna()].copy()
    if dataframe.empty:
        raise ValueError("No HDFS block IDs were found in the uploaded log.")

    dataframe["BlockId"] = dataframe["BlockId"].astype(str)
    event_counts = (
        dataframe.groupby(["BlockId", "EventId"], sort=False)
        .size()
        .unstack(fill_value=0)
    )

    for column in feature_columns:
        if column not in event_counts.columns:
            event_counts[column] = 0

    features = event_counts[feature_columns].fillna(0)
    if features.empty:
        raise ValueError("No analysable HDFS sessions were found in the file.")

    return features, features.index


def _anomaly_probability(model, features):
    class_values = list(model.classes_)
    for anomaly_label in (1, "1", "Anomaly", "anomaly"):
        if anomaly_label in class_values:
            return model.predict_proba(features)[:, class_values.index(anomaly_label)]
    raise ValueError("The model does not expose a recognised anomaly class.")


def predict_dataframe(dataframe: pd.DataFrame, source_name="uploaded.csv"):
    """Run inference for an in-memory DataFrame."""
    model, _ = load_model_assets()
    features, block_ids = extract_features(dataframe)

    predictions = model.predict(features)
    probabilities = _anomaly_probability(model, features)
    anomaly_labels = {1, "1", "Anomaly", "anomaly"}
    timestamp = pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")

    return pd.DataFrame(
        {
            "BlockId": [str(value) for value in block_ids],
            "Prediction": [
                "Anomaly" if value in anomaly_labels else "Normal"
                for value in predictions
            ],
            "Confidence": (probabilities * 100).round(2),
            "Timestamp": timestamp,
            "Source_File": Path(source_name).name,
        }
    )


def predict(log_file_path):
    """Run inference for a CSV path, preserving the original public API."""
    dataframe = _read_dataframe(log_file_path)
    return predict_dataframe(dataframe, source_name=Path(log_file_path).name)


def get_model_status():
    """Return serialisable runtime metadata for health checks."""
    model, feature_columns = load_model_assets()
    return {
        "ready": True,
        "algorithm": type(model).__name__,
        "trees": int(getattr(model, "n_estimators", 0)),
        "features": len(feature_columns),
        "model_file": MODEL_PATH.name,
    }
