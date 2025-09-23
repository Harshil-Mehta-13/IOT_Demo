import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- Page Config ---
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

# --- Fetch Data ---
@st.cache_data(ttl=5)
def get_sensor_data():
    try:
        response = (
            supabase_client.table("air_compressor")
            .select("*")
            .order("timestamp", desc=True)
            .limit(500)
            .execute()
        )
        data = response.data
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp").sort_index()
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# --- Tabs ---
tab1, tab2 = st.tabs(["📊 Dashboard", "📂 Database"])

# ============================================================
# TAB 1: DASHBOARD
# ============================================================
with tab1:
    st.markdown("## Air Compressor Monitoring ⚙️")

    df = get_sensor_data()

    if df.empty:
        st.warning("No data available. Waiting for ESP32 to push...")
    else:
        latest = df.iloc[-1]

        # --- KPI Metrics ---
        st.markdown("### Latest Readings")
        kpi1, kpi2, kpi3 = st.columns(3)

        # Temperature KPI
        temp_color = "🔴" if latest["temperature"] > 80 else ("🟠" if latest["temperature"] > 60 else "🟢")
        kpi1.metric("Temperature (°C)", f"{latest['temperature']:.2f}", help="Real-time temperature")
        kpi1.markdown(f"{temp_color} Status")

        # Pressure KPI
        pressure_color = "🔴" if latest["pressure"] > 12 else ("🟠" if latest["pressure"] > 9 else "🟢")
        kpi2.metric("Pressure (bar)", f"{latest['pressure']:.2f}")
        kpi2.markdown(f"{pressure_color} Status")

        # Vibration KPI
        vib_color = "🔴" if latest["vibration"] > 5 else ("🟠" if latest["vibration"] > 3 else "🟢")
        kpi3.metric("Vibration", f"{latest['vibration']:.2f}")
        kpi3.markdown(f"{vib_color} Status")

        # --- Charts ---
        st.markdown("### Historical Trends")
        c1, c2, c3 = st.columns(3)

        with c1:
            st.line_chart(df[["temperature"]], use_container_width=True)

        with c2:
            st.line_chart(df[["pressure"]], use_container_width=True)

        with c3:
            st.line_chart(df[["vibration"]], use_container_width=True)

        # --- Insights ---
        st.markdown("### Insights")
        avg_temp = df["temperature"].mean()
        avg_pressure = df["pressure"].mean()
        avg_vibration = df["vibration"].mean()

        st.info(
            f"📌 Average Temp: **{avg_temp:.2f}°C**, "
            f"Pressure: **{avg_pressure:.2f} bar**, "
            f"Vibration: **{avg_vibration:.2f}**"
        )

# ============================================================
# TAB 2: DATABASE
# ============================================================
with tab2:
    st.markdown("## Database Viewer")
    df_viewer = get_sensor_data()
    if df_viewer.empty:
        st.warning("No records in database.")
    else:
        st.dataframe(df_viewer, use_container_width=True, height=500)

        # CSV Download
        csv = df_viewer.to_csv().encode("utf-8")
        st.download_button(
            "⬇️ Download CSV",
            csv,
            "air_compressor_data.csv",
            "text/csv",
            key="download-csv"
        )

# ============================================================
# AUTO REFRESH
# ============================================================
import time
time.sleep(5)
st.rerun()
