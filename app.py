import streamlit as st
import pandas as pd
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

# --- Page Configuration ---
st.set_page_config(
    page_title="Air Compressor Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Auto Refresh every 5 seconds ---
st_autorefresh(interval=5000, key="data_refresh")

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
        st.error(f"Error fetching data from Supabase: {e}")
        return pd.DataFrame()

# --- Main Title ---
st.title("⚙️ Air Compressor Monitoring System")

# --- Tabs Layout ---
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🗄 Database", "📈 Reports"])

# ================= DASHBOARD =================
with tab1:
    df = get_sensor_data()

    if not df.empty:
        latest = df.iloc[-1]

        # Latest metrics
        st.subheader("Latest Readings")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("🌡 Temperature (°C)", f"{latest['temperature']:.2f}")
        with col2:
            st.metric("💧 Humidity (%)", f"{latest['humidity']:.2f}")
        with col3:
            st.metric("⏱ Pressure (bar)", f"{latest['pressure']:.2f}")
        with col4:
            st.metric("📳 Vibration", f"{latest['vibration']:.4f}")

        # Trend charts
        st.subheader("Historical Trends")
        chart_cols = st.columns(2)

        with chart_cols[0]:
            st.line_chart(df[["temperature", "humidity"]], use_container_width=True)

        with chart_cols[1]:
            st.line_chart(df[["pressure", "vibration"]], use_container_width=True)

    else:
        st.info("Waiting for data to arrive from the ESP32...")

# ================= DATABASE =================
with tab2:
    df = get_sensor_data()
    st.subheader("Database View")

    if not df.empty:
        st.dataframe(df, use_container_width=True, height=400)

        # Download as CSV
        csv = df.to_csv().encode("utf-8")
        st.download_button(
            "📥 Download Data as CSV",
            data=csv,
            file_name="air_compressor_data.csv",
            mime="text/csv",
        )
    else:
        st.warning("No data available yet.")

# ================= REPORTS =================
with tab3:
    df = get_sensor_data()
    st.subheader("Summary Reports")

    if not df.empty:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Avg Temp (°C)", f"{df['temperature'].mean():.2f}")
        with col2:
            st.metric("Avg Humidity (%)", f"{df['humidity'].mean():.2f}")
        with col3:
            st.metric("Avg Pressure (bar)", f"{df['pressure'].mean():.2f}")
        with col4:
            st.metric("Avg Vibration", f"{df['vibration'].mean():.4f}")

        st.subheader("Trend Overview")
        st.area_chart(df[["temperature", "pressure", "vibration"]], use_container_width=True)
    else:
        st.warning("No data available to generate reports.")
