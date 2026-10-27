from pathlib import Path
from datetime import datetime, timedelta
import io
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Big Data Intelligence", page_icon="📊", layout="wide")

APP_DIR = Path(__file__).resolve().parent
SAMPLE_PATHS = [
    APP_DIR / "sample_events.csv",
    APP_DIR / "data" / "sample_events.csv",  # backward compatibility
]

@st.cache_data
def generate_sample_data(n=2500, seed=42):
    """Create realistic demo events if the bundled CSV is unavailable."""
    rng = np.random.default_rng(seed)
    now = pd.Timestamp.now().floor("min")
    times = now - pd.to_timedelta(rng.integers(0, 30 * 24 * 60, n), unit="m")
    regions = rng.choice(["North", "South", "East", "West", "Central"], n)
    categories = rng.choice(["purchase", "view", "signup", "click", "refund"], n,
                            p=[.22, .36, .10, .27, .05])
    status = rng.choice(["success", "failed", "pending"], n, p=[.91, .06, .03])
    devices = rng.choice(["Mobile", "Desktop", "Tablet"], n, p=[.62, .32, .06])
    amounts = np.where(categories == "purchase", rng.gamma(3.2, 650, n), 0).round(2)
    frame = pd.DataFrame({
        "event_id": [f"EVT-{i:06d}" for i in range(1, n + 1)],
        "timestamp": times,
        "region": regions,
        "category": categories,
        "status": status,
        "device": devices,
        "amount": amounts,
        "latency_ms": rng.lognormal(mean=4.3, sigma=.45, size=n).round(1),
    })
    # Add a few intentional quality/anomaly examples for the dashboard demo.
    if n >= 30:
        frame.loc[3, "region"] = None
        frame.loc[7, "amount"] = -250
        frame.loc[12, "latency_ms"] = 4200
    return frame

@st.cache_data
def read_csv_bytes(contents):
    return pd.read_csv(io.BytesIO(contents))

def load_default_data():
    for path in SAMPLE_PATHS:
        try:
            if path.is_file():
                return pd.read_csv(path), f"Bundled sample: {path.name}"
        except Exception:
            pass
    return generate_sample_data(), "Generated demo data (sample CSV was not found)"

def normalize_columns(df):
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df

def ensure_fields(df):
    df = normalize_columns(df)
    # Accept common column aliases.
    aliases = {"time": "timestamp", "date": "timestamp", "event": "category",
               "type": "category", "status_code": "status", "location": "region",
               "value": "amount", "duration_ms": "latency_ms", "device_type": "device"}
    for old, new in aliases.items():
        if new not in df and old in df:
            df = df.rename(columns={old: new})
    defaults = {
        "event_id": [f"ROW-{i+1:06d}" for i in range(len(df))],
        "timestamp": pd.Timestamp.now(),
        "region": "Unknown", "category": "other", "status": "unknown",
        "device": "Unknown", "amount": 0.0, "latency_ms": np.nan,
    }
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for col in ["amount", "latency_ms"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["region", "category", "status", "device"]:
        df[col] = df[col].fillna("Unknown").astype(str)
    return df

st.title("📊 Big Data Intelligence")
st.caption("Interactive event analytics • data quality • anomaly detection • stream replay")

with st.sidebar:
    st.header("Data source")
    uploaded = st.file_uploader("Upload event CSV", type=["csv"])
    if uploaded:
        try:
            source_df = read_csv_bytes(uploaded.getvalue())
            source_label = f"Uploaded: {uploaded.name}"
        except Exception as exc:
            st.error(f"Could not read CSV: {exc}")
            source_df, source_label = load_default_data()
    else:
        source_df, source_label = load_default_data()
    st.caption(f"**Loaded:** {source_label}")
    st.divider()
    st.header("Filters")

df = ensure_fields(source_df)
valid_dates = df["timestamp"].dropna()
if valid_dates.empty:
    min_date = max_date = pd.Timestamp.now().date()
else:
    min_date, max_date = valid_dates.min().date(), valid_dates.max().date()

with st.sidebar:
    date_range = st.date_input("Date range", value=(min_date, max_date),
                               min_value=min_date, max_value=max_date)
    def multi_filter(label, col):
        choices = sorted(df[col].dropna().astype(str).unique().tolist())
        return st.multiselect(label, choices, default=choices)
    regions = multi_filter("Region", "region")
    categories = multi_filter("Category", "category")
    statuses = multi_filter("Status", "status")
    devices = multi_filter("Device", "device")
    st.divider()
    st.caption("Tip: upload your own CSV to explore your event data.")

filtered = df.copy()
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start = pd.Timestamp(date_range[0])
    end = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1)
    filtered = filtered[filtered["timestamp"].ge(start) & filtered["timestamp"].lt(end)]
for col, values in [("region", regions), ("category", categories),
                    ("status", statuses), ("device", devices)]:
    filtered = filtered[filtered[col].astype(str).isin(values)]

total = len(filtered)
success_rate = (filtered["status"].str.lower().eq("success").mean() * 100) if total else 0
revenue = filtered.loc[filtered["category"].str.lower().eq("purchase"), "amount"].clip(lower=0).sum()
avg_latency = filtered["latency_ms"].mean()

a, b, c, d = st.columns(4)
a.metric("Events", f"{total:,}")
b.metric("Success rate", f"{success_rate:.1f}%")
c.metric("Purchase value", f"₹{revenue:,.0f}")
d.metric("Avg latency", f"{avg_latency:,.0f} ms" if pd.notna(avg_latency) else "—")

tab_overview, tab_quality, tab_stream, tab_data = st.tabs(
    ["📈 Overview", "🧪 Data quality", "⚡ Stream simulator", "🗂️ Data explorer"])

with tab_overview:
    left, right = st.columns(2)
    with left:
        st.subheader("Events over time")
        timeline = filtered.dropna(subset=["timestamp"]).set_index("timestamp").resample("D").size()
        st.line_chart(timeline.rename("Events"))
    with right:
        st.subheader("Events by category")
        counts = filtered["category"].value_counts().rename_axis("Category").to_frame("Events")
        st.bar_chart(counts)
    lower_left, lower_right = st.columns(2)
    with lower_left:
        st.subheader("Regional activity")
        st.bar_chart(filtered["region"].value_counts())
    with lower_right:
        st.subheader("Status distribution")
        st.bar_chart(filtered["status"].value_counts())
    st.subheader("Device mix")
    st.bar_chart(filtered["device"].value_counts())

with tab_quality:
    st.subheader("Data quality checks")
    issues = []
    for col in df.columns:
        missing = int(df[col].isna().sum())
        if missing:
            issues.append({"Check": "Missing values", "Column": col, "Rows": missing, "Severity": "Review"})
    negative_amounts = int(df["amount"].lt(0).sum())
    if negative_amounts:
        issues.append({"Check": "Negative amount", "Column": "amount", "Rows": negative_amounts, "Severity": "Warning"})
    duplicates = int(df["event_id"].duplicated().sum())
    if duplicates:
        issues.append({"Check": "Duplicate event ID", "Column": "event_id", "Rows": duplicates, "Severity": "Warning"})
    invalid_times = int(df["timestamp"].isna().sum())
    if invalid_times:
        issues.append({"Check": "Invalid timestamp", "Column": "timestamp", "Rows": invalid_times, "Severity": "Review"})
    if issues:
        st.dataframe(pd.DataFrame(issues), use_container_width=True, hide_index=True)
    else:
        st.success("No issues found in the checked fields.")
    st.subheader("Latency anomaly flags")
    lat = filtered["latency_ms"].dropna()
    if len(lat) >= 4:
        q1, q3 = lat.quantile([.25, .75])
        upper = q3 + 1.5 * (q3 - q1)
        outliers = filtered[filtered["latency_ms"] > upper].sort_values("latency_ms", ascending=False)
        st.write(f"Rule: IQR upper fence = **{upper:.1f} ms** · flagged **{len(outliers)}** row(s)")
        st.dataframe(outliers.head(250), use_container_width=True, hide_index=True)
    else:
        st.info("Not enough valid latency values for anomaly checks.")

with tab_stream:
    st.subheader("Live-stream replay")
    st.write("Replay a slice of the selected events as if records were arriving in a stream.")
    stream_source = filtered.sort_values("timestamp", na_position="last")
    max_rows = len(stream_source)
    if max_rows:
        limit = st.slider("Events to replay", min_value=1, max_value=max_rows,
                          value=min(100, max_rows))
        if st.button("▶ Replay stream"):
            st.dataframe(stream_source.tail(limit), use_container_width=True, hide_index=True)
            st.success(f"Replay prepared: {min(limit, max_rows):,} event(s).")
    else:
        st.info("No events match the current filters.")

with tab_data:
    st.subheader("Filtered event records")
    st.caption(f"{len(filtered):,} rows · {len(filtered.columns)} columns")
    st.dataframe(filtered, use_container_width=True, height=420, hide_index=True)
    csv_out = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("⬇ Download filtered CSV", csv_out, "filtered_events.csv", "text/csv")
    summary = filtered.describe(include="all").transpose().reset_index(names="field")
    st.download_button("⬇ Download profile CSV", summary.to_csv(index=False).encode("utf-8"),
                       "data_profile.csv", "text/csv")

st.divider()
st.caption("Demo analytics for learning and prototyping. For production streaming, connect Kafka, Spark, or a managed event source.")
