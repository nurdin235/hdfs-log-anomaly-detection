"""Vercel Python function for HDFS log anomaly inference."""

from http.server import BaseHTTPRequestHandler
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote
import json
import sys

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.pipeline import get_model_status, predict_dataframe


MAX_UPLOAD_BYTES = 4 * 1024 * 1024
MAX_SESSIONS = 15_000


def assign_severity(confidence):
    if confidence >= 95:
        return "CRITICAL"
    if confidence >= 80:
        return "HIGH"
    if confidence >= 65:
        return "MEDIUM"
    return "LOW"


def serialise_records(dataframe):
    records = dataframe.to_dict(orient="records")
    for record in records:
        for key, value in tuple(record.items()):
            if hasattr(value, "item"):
                record[key] = value.item()
    return records


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, payload):
        body = json.dumps(payload, allow_nan=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Allow", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-File-Name")
        self.end_headers()

    def do_GET(self):
        try:
            self._send_json(
                200,
                {
                    "service": "HDFS anomaly detection API",
                    "status": "ready",
                    "upload_limit_bytes": MAX_UPLOAD_BYTES,
                    "model": get_model_status(),
                },
            )
        except Exception as exc:
            self._send_json(
                503,
                {
                    "status": "unavailable",
                    "error": f"Model could not be loaded: {exc}",
                },
            )

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0

        if content_length <= 0:
            self._send_json(400, {"error": "Upload a non-empty CSV file."})
            return
        if content_length > MAX_UPLOAD_BYTES:
            self._send_json(
                413,
                {
                    "error": "The file is larger than the 4 MB dashboard limit.",
                    "limit_bytes": MAX_UPLOAD_BYTES,
                },
            )
            return

        filename = unquote(self.headers.get("X-File-Name", "uploaded.csv"))
        filename = Path(filename).name or "uploaded.csv"

        try:
            payload = self.rfile.read(content_length)
            dataframe = pd.read_csv(BytesIO(payload))
            results = predict_dataframe(dataframe, source_name=filename)

            if len(results) > MAX_SESSIONS:
                self._send_json(
                    422,
                    {
                        "error": (
                            f"The file produced {len(results):,} sessions. "
                            f"Please upload at most {MAX_SESSIONS:,} sessions at once."
                        )
                    },
                )
                return

            anomaly_mask = results["Prediction"].eq("Anomaly")
            results["Severity"] = None
            results.loc[anomaly_mask, "Severity"] = results.loc[
                anomaly_mask, "Confidence"
            ].map(assign_severity)

            total = int(len(results))
            anomalies = int(anomaly_mask.sum())
            severity_counts = (
                results.loc[anomaly_mask, "Severity"].value_counts().to_dict()
            )

            self._send_json(
                200,
                {
                    "file": filename,
                    "summary": {
                        "total": total,
                        "normal": total - anomalies,
                        "anomalies": anomalies,
                        "anomaly_rate": round((anomalies / total) * 100, 2),
                        "severity": {
                            level: int(severity_counts.get(level, 0))
                            for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
                        },
                    },
                    "results": serialise_records(results),
                },
            )
        except (ValueError, UnicodeDecodeError, pd.errors.ParserError) as exc:
            self._send_json(400, {"error": str(exc)})
        except pd.errors.EmptyDataError:
            self._send_json(400, {"error": "The uploaded CSV is empty."})
        except Exception as exc:
            self._send_json(
                500,
                {"error": f"Analysis failed: {type(exc).__name__}: {exc}"},
            )
