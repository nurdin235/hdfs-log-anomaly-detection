# ── watcher.py ────────────────────────────────────────────────
# Watches the watch_folder 24/7 for new log files
# When a new file appears → runs pipeline → raises alerts automatically

import time
import os
import shutil
from watchdog.observers import Observer
from watchdog.events    import FileSystemEventHandler
from datetime           import datetime

# Import our pipeline and alerting modules
import sys
sys.path.append(os.path.dirname(__file__))
from pipeline  import predict
from alerting  import save_alerts

WATCH_FOLDER     = os.path.join(os.path.dirname(__file__), '..', 'watch_folder')
PROCESSED_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'processed')


class LogFileHandler(FileSystemEventHandler):
    """
    Automatically triggered when a new file
    is dropped into the watch_folder
    """

    def on_created(self, event):
        # Only process CSV and log files
        if event.is_directory:
            return

        file_path = event.src_path
        filename  = os.path.basename(file_path)

        if not filename.endswith(('.csv', '.log')):
            return

        print("\n" + "="*55)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] NEW FILE DETECTED: {filename}")
        print("="*55)

        # Wait briefly to ensure file is fully written
        time.sleep(2)

        try:
            # Step 1: Run prediction pipeline
            print("\n[STEP 1] Running prediction pipeline...")
            results = predict(file_path)

            # Step 2: Raise alerts
            print("\n[STEP 2] Checking for anomalies...")
            save_alerts(results)

            # Step 3: Move file to processed folder
            processed_path = os.path.join(PROCESSED_FOLDER, filename)
            shutil.move(file_path, processed_path)
            print(f"\n[STEP 3] File moved to: processed/{filename}")
            print("="*55)
            print("✅ Processing complete. Watching for next file...")

        except Exception as e:
            print(f"\n❌ ERROR processing {filename}: {e}")


def start_watcher():
    """
    Starts the automated file watcher
    Runs continuously until you press Ctrl+C
    """
    os.makedirs(WATCH_FOLDER,     exist_ok=True)
    os.makedirs(PROCESSED_FOLDER, exist_ok=True)

    print("="*55)
    print("  HDFS LOG ANOMALY DETECTION SYSTEM")
    print("  Automated File Watcher — RUNNING")
    print("="*55)
    print(f"  Watching : {WATCH_FOLDER}")
    print(f"  Drop any HDFS .csv or .log file into")
    print(f"  the watch_folder to trigger analysis")
    print("="*55)
    print("  Press Ctrl+C to stop\n")

    event_handler = LogFileHandler()
    observer      = Observer()
    observer.schedule(event_handler, WATCH_FOLDER, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n⛔ Watcher stopped.")

    observer.join()


if __name__ == "__main__":
    start_watcher()