import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime
import requests

# --- CONFIG: read from Streamlit secrets (set these when deploying)
SUPABASE_URL = st.secrets[]
SUPABASE_KEY = st.secrets[]

# ✅ Initialize Supabase client properly
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Air Compressor Monitor", layout="wide")
st.title("🛠 Air Compressor Monitoring Dashboard (Prototype)")

# --- Fetch data from Supabase
@st.cache_data(ttl=10)
def load_data():
    try:
        resp = supabase.table("air_compressor").select("*").order("timestamp", desc=True).execute()
        data = resp.data
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        # ensure timestamp is datetime
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("⚠ No data yet. Run the Wokwi/ESP32 simulator to send data.")
    st.stop()

# --- Sidebar filters
st.sidebar.header("Filters")
compressors = sorted(df["compressor_id"].unique())
selected_comp = st.sidebar.selectbox("Compressor", ["All"] + compressors)

min_dt = df["timestamp"].min()
max_dt = df["timestamp"].max()
start_date = st.sidebar.date_input("Start date", min_dt.date())
end_date = st.sidebar.date_input("End date", max_dt.date())

# filter df
mask = (df["timestamp"].dt.date >= start_date) & (df["timestamp"].dt.date <= end_date)
if selected_comp != "All":
    mask &= (df["compressor_id"] == selected_comp)
df_filt = df.loc[mask].sort_values("timestamp")

# --- Summary section
st.subheader("Summary")
col1, col2, col3 = st.columns(3)
if not df_filt.empty:
    col1.metric("Latest Pressure", f"{df_filt.iloc[-1]['pressure']:.2f} bar")
    col2.metric("Latest Temp", f"{df_filt.iloc[-1]['temperature']:.2f} °C")
    col3.metric("Records", len(df_filt))
else:
    col1.write("No data in range")

# --- Charts
st.subheader("📈 Time Series Trends")
if not df_filt.empty:
    chart_data = df_filt.set_index("timestamp")[["pressure", "temperature"]]
    st.line_chart(chart_data)

# --- Data log table
st.subheader("📋 Data Log")
st.dataframe(df_filt, use_container_width=True)

# --- CSV Download
@st.cache_data
def to_csv(df_):
    return df_.to_csv(index=False).encode("utf-8")

if not df_filt.empty:
    st.download_button("⬇ Download CSV", to_csv(df_filt), file_name="compressor_data.csv")
