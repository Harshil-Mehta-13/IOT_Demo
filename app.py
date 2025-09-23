import streamlit as st
import pandas as pd
from supabase import create_client, Client
import time
import plotly.graph_objects as go
import plotly.express as px

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

# --- Helper Functions for Status and Styling ---
def get_status_color(value, param_name):
    if param_name == 'temperature':
        if value > 80: return "#ff4b4b"
        elif value > 60: return "#ffcc00"
        else: return "#2ec27e"
    elif param_name == 'pressure':
        if value > 12: return "#ff4b4b"
        elif value > 9: return "#ffcc00"
        else: return "#2ec27e"
    elif param_name == 'vibration':
        if value > 5: return "#ff4b4b"
        elif value > 3: return "#ffcc00"
        else: return "#2ec27e"
    return "#2ec27e"

def get_status_text(value, param_name):
    if param_name == 'temperature':
        if value > 80: return "Critical"
        elif value > 60: return "Warning"
        else: return "Normal"
    elif param_name == 'pressure':
        if value > 12: return "Critical"
        elif value > 9: return "Warning"
        else: return "Normal"
    elif param_name == 'vibration':
        if value > 5: return "Critical"
        elif value > 3: return "Warning"
        else: return "Normal"
    return "Normal"

# --- Main App Logic ---
st.title("Air Compressor Monitoring Dashboard ⚙️")
st.markdown("A real-time dashboard for tracking key operational metrics.")

dashboard_placeholder = st.empty()

while True:
    df = get_sensor_data()

    with dashboard_placeholder.container():
        if df.empty:
            st.warning("No data available. Please check your ESP32 connection.")
        else:
            latest = df.iloc[-1]
            
            # --- Layout: KPI column on the left, charts on the right ---
            kpi_col, chart_col = st.columns([1, 3])

            with kpi_col:
                st.subheader("Latest Readings & Status")
                
                # Temperature KPI
                st.markdown(f"""
                    <div style="background-color: #262730; border-radius: 10px; padding: 20px; text-align: center; margin-bottom: 10px;">
                        <p style="font-size: 1.2em; font-weight: bold; color: #a4a4a4;">🌡️ Temperature (°C)</p>
                        <p style="font-size: 2.5em; font-weight: bold; color: {get_status_color(latest['temperature'], 'temperature')};">{latest['temperature']:.2f}</p>
                        <p style="color: #666; font-size: 1em;">Status: {get_status_text(latest['temperature'], 'temperature')}</p>
                    </div>
                """, unsafe_allow_html=True)
                
                # Pressure KPI
                st.markdown(f"""
                    <div style="background-color: #262730; border-radius: 10px; padding: 20px; text-align: center; margin-bottom: 10px;">
                        <p style="font-size: 1.2em; font-weight: bold; color: #a4a4a4;">PSI Pressure (bar)</p>
                        <p style="font-size: 2.5em; font-weight: bold; color: {get_status_color(latest['pressure'], 'pressure')};">{latest['pressure']:.2f}</p>
                        <p style="color: #666; font-size: 1em;">Status: {get_status_text(latest['pressure'], 'pressure')}</p>
                    </div>
                """, unsafe_allow_html=True)
                
                # Vibration KPI
                st.markdown(f"""
                    <div style="background-color: #262730; border-radius: 10px; padding: 20px; text-align: center;">
                        <p style="font-size: 1.2em; font-weight: bold; color: #a4a4a4;">📳 Vibration</p>
                        <p style="font-size: 2.5em; font-weight: bold; color: {get_status_color(latest['vibration'], 'vibration')};">{latest['vibration']:.2f}</p>
                        <p style="color: #666; font-size: 1em;">Status: {get_status_text(latest['vibration'], 'vibration')}</p>
                    </div>
                """, unsafe_allow_html=True)
            
            with chart_col:
                st.subheader("Historical Trends")
                
                # Three charts in a 3-column layout to prevent scrolling
                chart_col1, chart_col2, chart_col3 = st.columns(3)
                
                with chart_col1:
                    st.markdown("##### Temperature")
                    fig_temp = go.Figure()
                    fig_temp.add_trace(go.Scatter(x=df.index, y=df['temperature'], mode='lines', name='Temperature'))
                    fig_temp.add_hline(y=60, line
