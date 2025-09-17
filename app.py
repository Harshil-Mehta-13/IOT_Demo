import streamlit as st
import pandas as pd
from supabase import create_client
import datetime
import os
import requests

# --- CONFIG: read from Streamlit secrets (set these when deploying)
SUPABASE_URL = st.secrets["https://ynodggqmitbqluwmljjg.supabase.co"]
SUPABASE_KEY = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inlub2RnZ3FtaXRicWx1d21sampnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ0NzE1MDcsImV4cCI6MjA3MDA0NzUwN30.LTf5dUJL3Y4-bofHZ-pZ1mWAv60gX0FDON5uIzjgCWM"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Air Compressor Monitor", layout="wide")
st.title("Air Compressor Monitoring Dashboard (Prototype)")

# Fetch data from Supabase
@st.cache_data(ttl=10)
def load_data():
    resp = supabase.table("air_compressor").select("*").order("timestamp", {"ascending": False}).execute()
    data = resp.data
    if data is None:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    # ensure timestamp is datetime
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

df = load_data()

if df.empty:
    st.warning("No data yet. Run the Wokwi/ESP32 simulator to send data.")
    st.stop()

# Sidebar filters
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

st.subheader("Summary")
col1, col2, col3 = st.columns(3)
if not df_filt.empty:
    col1.metric("Latest Pressure", f"{df_filt.iloc[-1]['pressure']:.2f} bar")
    col2.metric("Latest Temp", f"{df_filt.iloc[-1]['temperature']:.2f} °C")
    col3.metric("Records", len(df_filt))
else:
    col1.write("No data in range")

# Charts
st.subheader("Time Series")
if not df_filt.empty:
    chart_data = df_filt.set_index("timestamp")[["pressure", "temperature"]]
    st.line_chart(chart_data)

# Data log table
st.subheader("Data Log")
st.dataframe(df_filt, use_container_width=True)

# CSV Download
@st.cache_data
def to_csv(df_):
    return df_.to_csv(index=False).encode("utf-8")

if not df_filt.empty:
    st.download_button("Download CSV", to_csv(df_filt), file_name="compressor_data.csv")

# Simple alert check (example)
st.subheader("Alerts")
alert_rows = df_filt[df_filt["pressure"] < 5.0]  # threshold example
if not alert_rows.empty:
    st.error(f"Low pressure alerts: {len(alert_rows)} records found.")
    st.write(alert_rows[["timestamp", "compressor_id", "pressure"]].tail(10))
    # OPTIONAL: send Telegram alerts — set TELEGRAM_TOKEN & CHAT_ID in secrets if you want
    if "TELEGRAM_TOKEN" in st.secrets and "TELEGRAM_CHAT_ID" in st.secrets:
        if st.button("Send Telegram Alert (manual)"):
            token = st.secrets["TELEGRAM_TOKEN"]
            chat_id = st.secrets["TELEGRAM_CHAT_ID"]
            text = f"Alert: low pressure for {selected_comp if selected_comp!='All' else 'multiple compressors'}"
            requests.get(f"https://api.telegram.org/bot{token}/sendMessage", params={"chat_id": chat_id, "text": text})
            st.success("Sent telegram alert (manual).")
else:
    st.success("No alerts (pressure OK).")
