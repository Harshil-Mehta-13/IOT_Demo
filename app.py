import streamlit as st
import pandas as pd
from supabase import create_client, Client
import time
import plotly.express as px
import plotly.graph_objects as go

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

# --- Helper Functions ---
def get_status_color(value, param_name):
    if param_name == 'temperature':
        if value > 80:
            return "#ff4b4b" # red
        elif value > 60:
            return "#ffcc00" # orange
        else:
            return "#2ec27e" # green
    elif param_name == 'pressure':
        if value > 12:
            return "#ff4b4b"
        elif value > 9:
            return "#ffcc00"
        else:
            return "#2ec27e"
    elif param_name == 'vibration':
        if value > 5:
            return "#ff4b4b"
        elif value > 3:
            return "#ffcc00"
        else:
            return "#2ec27e"
    return "#2ec27e"

def get_status_text(value, param_name):
    if param_name == 'temperature':
        if value > 80:
            return "Critical"
        elif value > 60:
            return "Warning"
        else:
            return "Normal"
    elif param_name == 'pressure':
        if value > 12:
            return "Critical"
        elif value > 9:
            return "Warning"
        else:
            return "Normal"
    elif param_name == 'vibration':
        if value > 5:
            return "Critical"
        elif value > 3:
            return "Warning"
        else:
            return "Normal"
    return "Normal"

# --- Main App Logic ---
st.title("Air Compressor Monitoring Dashboard ⚙️")
st.markdown("A real-time dashboard for tracking key operational metrics of an air compressor.")

# Fetch the data
df = get_sensor_data()

# --- Tabs ---
tab1, tab2 = st.tabs(["📊 Dashboard", "📂 Database"])

with tab1:
    if df.empty:
        st.warning("No data available. Please check your ESP32 connection.")
    else:
        latest = df.iloc[-1]
        
        # --- KPI Cards ---
        st.subheader("Latest Readings & Status")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"""
                <div style="
                    background-color: #f0f2f6;
                    border-radius: 10px;
                    padding: 20px;
                    text-align: center;
                ">
                    <p style="font-size: 1.2em; font-weight: bold;">🌡️ Temperature (°C)</p>
                    <p style="font-size: 2.5em; font-weight: bold; color: {get_status_color(latest['temperature'], 'temperature')};">{latest['temperature']:.2f}</p>
                    <p style="color: #666; font-size: 1em;">Status: {get_status_text(latest['temperature'], 'temperature')}</p>
                </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
                <div style="
                    background-color: #f0f2f6;
                    border-radius: 10px;
                    padding: 20px;
                    text-align: center;
                ">
                    <p style="font-size: 1.2em; font-weight: bold;">PSI Pressure (bar)</p>
                    <p style="font-size: 2.5em; font-weight: bold; color: {get_status_color(latest['pressure'], 'pressure')};">{latest['pressure']:.2f}</p>
                    <p style="color: #666; font-size: 1em;">Status: {get_status_text(latest['pressure'], 'pressure')}</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
                <div style="
                    background-color: #f0f2f6;
                    border-radius: 10px;
                    padding: 20px;
                    text-align: center;
                ">
                    <p style="font-size: 1.2em; font-weight: bold;">📳 Vibration</p>
                    <p style="font-size: 2.5em; font-weight: bold; color: {get_status_color(latest['vibration'], 'vibration')};">{latest['vibration']:.2f}</p>
                    <p style="color: #666; font-size: 1em;">Status: {get_status_text(latest['vibration'], 'vibration')}</p>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # --- Trend Chart ---
        st.subheader("Historical Trends")
        
        df_melt = df.reset_index().melt('timestamp', var_name='Parameter', value_name='Value')
        fig = px.line(df_melt, x='timestamp', y='Value', color='Parameter',
                      title='Combined Sensor Trends')
        
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Raw Database Data")
    if df.empty:
        st.warning("No records in database.")
    else:
        st.dataframe(df, use_container_width=True, height=500)
        
        # Download button
        csv = df.to_csv().encode('utf-8')
        st.download_button(
            "⬇️ Download CSV",
            csv,
            "air_compressor_data.csv",
            "text/csv",
            key='download-csv'
        )

# --- Auto Refresh ---
time.sleep(5)
st.rerun()
