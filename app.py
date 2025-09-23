import streamlit as st
import pandas as pd
from supabase import create_client, Client
import time
import plotly.graph_objects as go
import pytz
from datetime import datetime, timedelta

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

# --- Helper Functions for Data Fetching and Styling ---
def get_live_data():
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

def get_historical_data(start_time):
    try:
        response = (
            supabase_client.table("air_compressor")
            .select("*")
            .gte("timestamp", start_time.isoformat())
            .order("timestamp", desc=True)
            .execute()
        )
        data = response.data
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        ist = pytz.timezone('Asia/Kolkata')
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert(ist)
        df = df.set_index("timestamp").sort_index()
        return df
    except Exception as e:
        st.error(f"Error fetching historical data: {e}")
        return pd.DataFrame()

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

def create_chart(df, param_name, title, color, warn_thresh=None, crit_thresh=None, height=300):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df[param_name], mode='lines', name=title, line=dict(color=color)))
    
    if warn_thresh:
        fig.add_hline(y=warn_thresh, line_dash="dash", line_color="orange", annotation_text="Warning", annotation_position="top left")
    if crit_thresh:
        fig.add_hline(y=crit_thresh, line_dash="dash", line_color="red", annotation_text="Critical", annotation_position="top left")

    fig.update_layout(
        height=height,
        margin={"l": 10, "r": 10, "t": 30, "b": 0},
        title=dict(text=title, font=dict(size=14)),
        template="plotly_dark",
        xaxis_title=None,
        yaxis_title=None,
        showlegend=False
    )
    return fig

# --- Main App Logic ---
st.title("Air Compressor Monitoring Dashboard ⚙️")
st.markdown("A real-time dashboard for tracking key operational metrics.")

with st.sidebar:
    st.header("Navigation")
    app_mode = st.radio("Choose a page", ["Live Dashboard", "Database"])

if app_mode == "Live Dashboard":
    live_placeholder = st.empty()
    while True:
        live_df = get_live_data()
        with live_placeholder.container():
            if live_df.empty:
                st.warning("No data available. Please check your ESP32 connection.")
            else:
                latest = live_df.iloc[-1]
                
                kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

                with kpi_col1:
                    st.metric(label="🌡️ Temp (°C)", value=f"{latest['temperature']:.2f}")
                    st.markdown(f"**Status:** <span style='color: {get_status_color(latest['temperature'], 'temperature')};'>{get_status_text(latest['temperature'], 'temperature')}</span>", unsafe_allow_html=True)
                with kpi_col2:
                    st.metric(label="PSI Pressure (bar)", value=f"{latest['pressure']:.2f}")
                    st.markdown(f"**Status:** <span style='color: {get_status_color(latest['pressure'], 'pressure')};'>{get_status_text(latest['pressure'], 'pressure')}</span>", unsafe_allow_html=True)
                with kpi_col3:
                    st.metric(label="📳 Vibration", value=f"{latest['vibration']:.2f}")
                    st.markdown(f"**Status:** <span style='color: {get_status_color(latest['vibration'], 'vibration')};'>{get_status_text(latest['vibration'], 'vibration')}</span>", unsafe_allow_html=True)

                st.markdown("---")
                
                st.subheader("Historical Trends (Last 100 Entries)")
                
                chart_col1, chart_col2, chart_col3 = st.columns(3)
                
                with chart_col1:
                    st.markdown("##### Temperature Trend")
                    fig_temp = create_chart(live_df, 'temperature', '', '#00BFFF', 60, 80, height=250)
                    st.plotly_chart(fig_temp, use_container_width=True, key=f"live_temp_{time.time()}")
                
                with chart_col2:
                    st.markdown("##### Pressure Trend")
                    fig_pressure = create_chart(live_df, 'pressure', '', '#88d8b0', 9, 12, height=250)
                    st.plotly_chart(fig_pressure, use_container_width=True, key=f"live_pressure_{time.time()}")
                
                with chart_col3:
                    st.markdown("##### Vibration Trend")
                    fig_vibration = create_chart(live_df, 'vibration', '', '#6a5acd', 3, 5, height=250)
                    st.plotly_chart(fig_vibration, use_container_width=True, key=f"live_vibration_{time.time()}")
        
        time.sleep(5)

elif app_mode == "Database":
    st.subheader("Raw Database Data")
    
    col_start, col_end, col_param = st.columns(3)
    with col_start:
        start_date = st.date_input("Start Date", value=datetime.now().date() - timedelta(days=7))
    with col_end:
        end_date = st.date_input("End Date", value=datetime.now().date())
    with col_param:
        parameters = ['temperature', 'pressure', 'vibration']
        selected_params = st.multiselect("Select Parameter(s) to Filter:", options=parameters, default=parameters)
    
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    try:
        ist = pytz.timezone('Asia/Kolkata')
        start_dt_utc = ist.localize(start_dt, is_dst=None).astimezone(pytz.utc)
        end_dt_utc = ist.localize(end_dt, is_dst=None).astimezone(pytz.utc)
        
        response = supabase_client.table("air_compressor").select("*").gte("timestamp", start_dt_utc.isoformat()).lte("timestamp", end_dt_utc.isoformat()).execute()
        
        filtered_df = pd.DataFrame(response.data)
        if filtered_df.empty:
            st.warning("No records found for the selected date range.")
        else:
            if selected_params:
                cols_to_display = ['timestamp'] + selected_params
                filtered_df = filtered_df[cols_to_display]
            else:
                st.warning("Please select at least one parameter.")
                filtered_df = pd.DataFrame()

            if not filtered_df.empty:
                st.dataframe(filtered_df, use_container_width=True, height=500)
                
                csv = filtered_df.to_csv().encode('utf-8')
                st.download_button(
                    "⬇️ Download Filtered CSV",
                    csv,
                    "filtered_data.csv",
                    "text/csv",
                    key='download_filtered'
                )
            
    except Exception as e:
        st.error(f"Error fetching data: {e}")
