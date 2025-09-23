import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="Air Compressor Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Supabase Connection ---
@st.cache_resource(ttl="30s")
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase_client = init_connection()

# --- Functions to Fetch Data ---
@st.cache_data(ttl=5)
def get_sensor_data(limit=500):
    response = supabase_client.table("air_compressor").select("*").order("timestamp", desc=True).limit(limit).execute()
    data = response.data
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()
    return df

# --- Tabs ---
tab_dashboard, tab_database, tab_reports = st.tabs(["📊 Dashboard", "📂 Database", "📈 Reports"])

# ---------------- Dashboard Tab ----------------
with tab_dashboard:
    st.header("Air Compressor Monitoring ⚙️")

    df = get_sensor_data()

    if df.empty:
        st.warning("No data found in Supabase.")
    else:
        latest_data = df.iloc[-1]

        # Latest readings
        col1, col2, col3 = st.columns(3)
        col1.metric("Temperature (°C)", f"{latest_data['temperature']:.2f}")
        col2.metric("Pressure (bar)", f"{latest_data['pressure']:.2f}")
        col3.metric("Vibration", f"{latest_data['vibration']:.4f}")

        # Summary values
        st.subheader("Summary Statistics")
        col4, col5, col6 = st.columns(3)
        col4.metric("Avg Temp (°C)", f"{df['temperature'].mean():.2f}")
        col5.metric("Avg Pressure (bar)", f"{df['pressure'].mean():.2f}")
        col6.metric("Avg Vibration", f"{df['vibration'].mean():.4f}")

        # Charts grid (non-scrolling)
        st.subheader("Trends")
        chart_col1, chart_col2, chart_col3 = st.columns(3)
        with chart_col1:
            st.line_chart(df[["temperature"]], use_container_width=True)
        with chart_col2:
            st.line_chart(df[["pressure"]], use_container_width=True)
        with chart_col3:
            st.line_chart(df[["vibration"]], use_container_width=True)

# ---------------- Database Tab ----------------
with tab_database:
    st.header("Database Viewer 📂")
    df = get_sensor_data(limit=1000)

    if df.empty:
        st.info("No data available.")
    else:
        st.dataframe(df, use_container_width=True, height=400)

        # Download button
        csv = df.to_csv().encode("utf-8")
        st.download_button(
            label="⬇️ Download CSV",
            data=csv,
            file_name=f"air_compressor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

# ---------------- Reports Tab ----------------
with tab_reports:
    st.header("Reports & Insights 📈")
    st.info("This section can include monthly averages, anomaly detection, or custom KPIs.")
