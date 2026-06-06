# HDFS Log Anomaly Detection Dashboard

A deployable security operations dashboard for detecting anomalous HDFS block
sessions with the trained Random Forest model in `model/rf_model.pkl`.

## Vercel Dashboard

The production interface is a static browser dashboard backed by the Python
function at `api/analyze.py`. It includes:

- Real model inference for structured HDFS CSV logs and E1-E29 feature matrices
- Dashboard metrics, severity distribution, and recent analysis activity
- Searchable results and alert logs
- CSV downloads for results and filtered alerts
- Browser-persistent alert history
- A bundled HDFS session matrix for one-click testing of every severity tier

Uploaded files are processed in memory. They are not written to Vercel's
filesystem or retained by the server.

## Deploy To Vercel

1. Push this repository to GitHub.
2. In [Vercel](https://vercel.com/new), import the GitHub repository.
3. Leave **Framework Preset** as `Other`.
4. Leave the build and output settings empty.
5. Select **Deploy**.

No environment variables or external database are required. Vercel will install
the pinned packages in `requirements.txt`, use Python 3.12 from
`.python-version`, and expose `api/analyze.py` at `/api/analyze`.

After deployment:

1. Open the generated Vercel URL.
2. Confirm the sidebar says **Model online**.
3. Open **Upload & Analyse**.
4. Select **Use included sample**.
5. Run the analysis and inspect the generated alerts and CSV downloads.

The included feature matrix contains representative session patterns designed
to exercise normal predictions and all four alert severity tiers. The separate
`HDFS_2k.log_structured.csv` file remains available for raw structured-log
schema testing.

The browser stores dashboard history locally on the test device. Clearing site
data or selecting **Clear history** removes that history.

## Local Verification

Install the Python runtime:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the local dashboard and API:

```powershell
.\.venv\Scripts\python.exe scripts\dev_server.py
```

Then open `http://127.0.0.1:4173`.

The original Streamlit dashboard remains in `dashboard/app.py` for local use,
but Vercel serves `index.html` because Streamlit requires a persistent WebSocket
server.

## API

`GET /api/analyze` checks model readiness.

`POST /api/analyze` accepts raw CSV bytes with:

```text
Content-Type: text/csv
X-File-Name: example.csv
```

The dashboard enforces a 4 MB upload limit so requests remain below Vercel's
4.5 MB function request limit.

## Dataset

The project uses the LogHub HDFS v1 dataset:

- Wei Xu et al., "Detecting Large-Scale System Problems by Mining Console
  Logs," SOSP 2009.
- Jieming Zhu et al., "Loghub: A Large Collection of System Log Datasets for
  AI-driven Log Analytics," ISSRE 2023.

## Deployment References

- [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python)
- [Vercel Function limits](https://vercel.com/docs/functions/limitations)
- [Vercel project configuration](https://vercel.com/docs/project-configuration/vercel-json)
