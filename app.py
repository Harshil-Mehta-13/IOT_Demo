import streamlit as st
import pandas as pd
from supabase import create_client, Client
import time
import plotly.graph_objects as go
import pytz

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
            .limit(100)
            .execute()
        )
        data = response.data
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        # Convert UTC timestamp to IST
        ist = pytz.timezone('Asia/Kolkata')
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert(ist)
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
        tab1, tab2 = st.tabs(["📊 Dashboard", "📂 Database"])

        with tab1:
            if df.empty:
                st.warning("No data available. Please check your ESP32 connection.")
            else:
                latest = df.iloc[-1]
                
                # --- KPI Cards with spacing ---
                st.subheader("Latest Readings & Status")
                kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

                with kpi_col1:
                    st.metric(label="🌡️ Temperature (°C)", value=f"{latest['temperature']:.2f}")
                    st.markdown(f"**Status:** <span style='color: {get_status_color(latest['temperature'], 'temperature')};'>{get_status_text(latest['temperature'], 'temperature')}</span>", unsafe_allow_html=True)
                    
                with kpi_col2:
                    st.metric(label="PSI Pressure (bar)", value=f"{latest['pressure']:.2f}")
                    st.markdown(f"**Status:** <span style='color: {get_status_color(latest['pressure'], 'pressure')};'>{get_status_text(latest['pressure'], 'pressure')}</span>", unsafe_allow_html=True)
                
                with kpi_col3:
                    st.metric(label="📳 Vibration", value=f"{latest['vibration']:.2f}")
                    st.markdown(f"**Status:** <span style='color: {get_status_color(latest['vibration'], 'vibration')};'>{get_status_text(latest['vibration'], 'vibration')}</span>", unsafe_allow_html=True)

                st.markdown("---")
                
                # --- Charts in a 3-column layout to prevent scrolling ---
                st.subheader("Historical Trends")
                
                chart_col1, chart_col2, chart_col3 = st.columns(3)

                with chart_col1:
                    st.markdown("##### Temperature Trend")
                    fig_temp = go.Figure()
                    fig_temp.add_trace(go.Scatter(x=df.index, y=df['temperature'], mode='lines', name='Temperature'))
                    fig_temp.add_hline(y=60, line_dash="dash", line_color="orange", annotation_text="Warning")
                    fig_temp.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="Critical")
                    fig_temp.update_layout(height=350, margin={"l": 10, "r": 10, "t": 30, "b": 0})
                    st.plotly_chart(fig_temp, use_container_width=True, key=f"temp_chart_{time.time()}")
    
                with chart_col2:
                    st.markdown("##### Pressure Trend")
                    fig_pressure = go.Figure()
                    fig_pressure.add_trace(go.Scatter(x=df.index, y=df['pressure'], mode='lines', name='Pressure', line_color='#88d8b0'))
                    fig_pressure.add_hline(y=9, line_dash="dash", line_color="orange", annotation_text="Warning")
                    fig_pressure.add_hline(y=12, line_dash="dash", line_color="red", annotation_text="Critical")
                    fig_pressure.update_layout(height=350, margin={"l": 10, "r": 10, "t": 30, "b": 0})
                    st.plotly_chart(fig_pressure, use_container_width=True, key=f"pressure_chart_{time.time()}")
    
                with chart_col3:
                    st.markdown("##### Vibration Trend")
                    fig_vibration = go.Figure()
                    fig_vibration.add_trace(go.Scatter(x=df.index, y=df['vibration'], mode='lines', name='Vibration', line_color='#6a5acd'))
                    fig_vibration.add_hline(y=3, line_dash="dash", line_color="orange", annotation_text="Warning")
                    fig_vibration.add_hline(y=5, line_dash="dash", line_color="red", annotation_text="Critical")
                    fig_vibration.update_layout(height=350, margin={"l": 10, "r": 10, "t": 30, "b": 0})
                    st.plotly_chart(fig_vibration, use_container_width=True, key=f"vibration_chart_{time.time()}")
            
        with tab2:
            st.subheader("Raw Database Data")
            if df.empty:
                st.warning("No records in database.")
            else:
                st.dataframe(df, use_container_width=True, height=500)
                
                csv = df.to_csv().encode('utf-8')
                st.download_button(
                    "⬇️ Download CSV",
                    csv,
                    "air_compressor_data.csv",
                    "text/csv",
                    key=f'download-csv_{time.time()}'
                )
    
    time.sleep(5)
