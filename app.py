import streamlit as st
import pandas as pd
from supabase import create_client
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="Air Compressor Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Supabase Connection ---
@st.cache_resource(ttl="30s")
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase_client = init_connection()

# --- Fetch Sensor Data ---
@st.cache_data(ttl=5)
def get_sensor_data():
    try:
        response = (
            supabase_client.table("air_compressor")
            .select("*")
            .order("timestamp", desc=True)
            .limit(300)
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
        st.error(f"Error fetching data from Supabase: {e}")
        return pd.DataFrame()

# --- Auto-refresh every 5s ---
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > 5:
    st.session_state.last_refresh = time.time()
    st.experimental_rerun()

# --- Tabs ---
tab1, tab2 = st.tabs(["📊 Dashboard", "🗄 Database"])

# ================= DASHBOARD =================
with tab1:
    df = get_sensor_data()

    st.markdown("### ⚙️ Air Compressor Live Monitoring")

    if not df.empty:
        latest = df.iloc[-1]

        # --- KPIs Row ---
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("🌡 Temperature (°C)", f"{latest['temperature']:.2f}")
        kpi2.metric("⏱ Pressure (bar)", f"{latest['pressure']:.2f}")
        kpi3.metric("📳 Vibration", f"{latest['vibration']:.4f}")

        # --- Charts Row ---
        st.markdown("#### Trends")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.line_chart(df[["temperature"]], use_container_width=True)
        with c2:
            st.line_chart(df[["pressure"]], use_container_width=True)
        with c3:
            st.line_chart(df[["vibration"]], use_container_width=True)

        # --- Insights Row ---
        st.markdown("#### Insights")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"🔹 **Max Temperature:** {df['temperature'].max():.2f} °C")
            st.write(f"🔹 **Min Temperature:** {df['temperature'].min():.2f} °C")
            st.write(f"🔹 **Avg Temperature:** {df['temperature'].mean():.2f} °C")

        with col2:
            st.write(f"🔸 **Max Pressure:** {df['pressure'].max():.2f} bar")
            st.write(f"🔸 **Avg Vibration:** {df['vibration'].mean():.4f}")
            st.write(f"🔸 **Last Updated:** {latest.name}")

    else:
        st.warning("No data received yet. Waiting for ESP32 readings...")

# ================= DATABASE =================
with tab2:
    st.markdown("### 🗄 Database Records")
    df = get_sensor_data()
    if not df.empty:
        st.dataframe(df, use_container_width=True, height=400)
        csv = df.to_csv().encode("utf-8")
        st.download_button("📥 Download CSV",
                           data=csv,
                           file_name="air_compressor_data.csv",
                           mime="text/csv")
    else:
        st.info("Database is empty.")
