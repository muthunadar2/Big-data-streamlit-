# Big Data Intelligence — Streamlit

An interactive event analytics dashboard with:
- KPI cards and time/category/region/status/device charts
- Sidebar filters and date range
- CSV upload and filtered CSV/profile downloads
- Data quality checks and IQR latency anomaly flags
- Lightweight stream replay preview
- **Resilient sample-data handling**: loads `data/sample_events.csv` using a path relative to `app.py`; if the bundled CSV is missing, generates demo data instead of crashing with `FileNotFoundError`.

## Run locally
Python 3.10+ recommended.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Community Cloud
1. Extract this ZIP and push the *contents* to the root of a GitHub repository.
2. Confirm `app.py`, `requirements.txt`, and `sample_events.csv` are committed in the same root folder.
3. Create/select the Streamlit app with `app.py` as the main file.
4. If replacing files in an existing repo, upload all four main files together—not only `app.py`.
5. Reboot the app from Streamlit's app management page.

## CSV format
Recommended columns: `event_id,timestamp,region,category,status,device,amount,latency_ms`.
Common alternatives like `date`, `time`, `event`, `type`, `location`, `value`, and `duration_ms` are normalized automatically. Missing optional fields are filled with defaults.

This is an educational analytics prototype, not a production distributed processing stack. For true high-volume streaming, integrate a broker/engine such as Kafka and Spark.
