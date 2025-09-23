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

def create_chart(df, param_name, title, color, warn_thresh=None, crit_thresh=None):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df[param_name], mode='lines', name=title, line=dict(color=color)))
    
    if warn_thresh:
        fig.add_hline(y=warn_thresh, line_dash="dash", line_color="orange", annotation_text="Warning", annotation_position="top left")
    if crit_thresh:
        fig.add_hline(y=crit_thresh, line_dash="dash", line_color="red", annotation_text="Critical", annotation_position="top left")

    fig.update_layout(
        height=300,
        margin={"l": 0, "r": 0, "t": 30, "b": 0},
        title=dict(text=title, font=dict(size=14)),
        template="plotly_dark",
        xaxis_title=None,
        yaxis_title=None,
        showlegend=False
    )
    return fig

# --- Main App Logic ---
st.title("Air Compressor Monitoring Dashboard ⚙️")

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
                
                # --- KPI Cards ---
                kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

                with kpi_col1:
                    st.markdown(f"""
                        <div style="
                            background-color: #262730;
                            border-radius: 10px;
                            padding: 10px;
                            text-align: center;
                            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                        ">
                            <p style="font-size: 1.1em; font-weight: bold; color: #a4a4a4;">🌡️ Temp (°C)</p>
                            <p style="font-size: 1.5em; font-weight: bold; color: {get_status_color(latest['temperature'], 'temperature')};">{latest['temperature']:.2f}</p>
                            <p style="color: #666; font-size: 0.8em;">Status: {get_status_text(latest['temperature'], 'temperature')}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                with kpi_col2:
                    st.markdown(f"""
                        <div style="
                            background-color: #262730;
                            border-radius: 10px;
                            padding: 10px;
                            text-align: center;
                            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                        ">
                            <p style="font-size: 1.1em; font-weight: bold; color: #a4a4a4;">PSI Pressure (bar)</p>
                            <p style="font-size: 1.5em; font-weight: bold; color: {get_status_color(latest['pressure'], 'pressure')};">{latest['pressure']:.2f}</p>
                            <p style="color: #666; font-size: 0.8em;">Status: {get_status_text(latest['pressure'], 'pressure')}</p>
                        </div>
                    """, unsafe_allow_html=True)
                
                with kpi_col3:
                    st.markdown(f"""
                        <div style="
                            background-color: #262730;
                            border-radius: 10px;
                            padding: 10px;
                            text-align: center;
                            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                        ">
                            <p style="font-size: 1.1em; font-weight: bold; color: #a4a4a4;">📳 Vibration</p>
                            <p style="font-size: 1.5em; font-weight: bold; color: {get_status_color(latest['vibration'], 'vibration')};">{latest['vibration']:.2f}</p>
                            <p style="color: #666; font-size: 0.8em;">Status: {get_status_text(latest['vibration'], 'vibration')}</p>
                        </div>
                    """, unsafe_allow_html=True)

                st.markdown("---")
                
                # --- Charts in a 3-column layout to prevent scrolling ---
                st.subheader("Historical Trends")
                
                chart_col1, chart_col2, chart_col3 = st.columns(3)

                with chart_col1:
                    fig_temp = create_chart(df, 'temperature', 'Temperature Trend', '#00BFFF', 60, 80)
                    st.plotly_chart(fig_temp, use_container_width=True, key=f"temp_chart_{time.time()}")
    
                with chart_col2:
                    fig_pressure = create_chart(df, 'pressure', 'Pressure Trend', '#88d8b0', 9, 12)
                    st.plotly_chart(fig_pressure, use_container_width=True, key=f"pressure_chart_{time.time()}")
    
                with chart_col3:
                    fig_vibration = create_chart(df, 'vibration', 'Vibration Trend', '#6a5acd', 3, 5)
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
