import streamlit as st
import pandas as pd
from supabase import create_client, Client
import time
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

# --- Helper Function for Status ---
def get_status_color(value, param_name):
    if param_name == 'temperature':
        if value > 80:
            return "critical"
        elif value > 60:
            return "warning"
        else:
            return "normal"
    elif param_name == 'pressure':
        if value > 12:
            return "critical"
        elif value > 9:
            return "warning"
        else:
            return "normal"
    elif param_name == 'vibration':
        if value > 5:
            return "critical"
        elif value > 3:
            return "warning"
        else:
            return "normal"
    return "normal"

# --- Main App Logic ---
st.title("Air Compressor Monitoring Dashboard ⚙️")

# Fetch the data at the start of the script run
df = get_sensor_data()

# A list of parameters to display
parameters = ['temperature', 'pressure', 'vibration']

# --- Sidebar for controls ---
with st.sidebar:
    st.header("Dashboard Controls")
    selected_parameter = st.selectbox(
        'Select a parameter to view:',
        options=parameters,
        key='parameter_selectbox'
    )
    st.info("The dashboard auto-refreshes every 5 seconds.")

# --- Tabs ---
tab1, tab2 = st.tabs(["📊 Dashboard", "📂 Database"])

# ============================================================
# TAB 1: DASHBOARD
# ============================================================
with tab1:
    if df.empty:
        st.warning("No data available. Waiting for ESP32 to push...")
    else:
        latest = df.iloc[-1]
        
        # --- KPI Cards ---
        st.subheader("Latest Readings")
        col1, col2, col3 = st.columns(3)

        # Temperature KPI Card
        temp_status = get_status_color(latest["temperature"], 'temperature')
        col1.metric("Temperature (°C)", f"{latest['temperature']:.2f}", help="Real-time temperature")
        col1.markdown(f"**Status:** <span style='color: {'red' if temp_status == 'critical' else 'orange' if temp_status == 'warning' else 'green'};'>{temp_status.capitalize()}</span>", unsafe_allow_html=True)
        
        # Pressure KPI Card
        pressure_status = get_status_color(latest["pressure"], 'pressure')
        col2.metric("Pressure (bar)", f"{latest['pressure']:.2f}")
        col2.markdown(f"**Status:** <span style='color: {'red' if pressure_status == 'critical' else 'orange' if pressure_status == 'warning' else 'green'};'>{pressure_status.capitalize()}</span>", unsafe_allow_html=True)
        
        # Vibration KPI Card
        vibration_status = get_status_color(latest["vibration"], 'vibration')
        col3.metric("Vibration", f"{latest['vibration']:.2f}")
        col3.markdown(f"**Status:** <span style='color: {'red' if vibration_status == 'critical' else 'orange' if vibration_status == 'warning' else 'green'};'>{vibration_status.capitalize()}</span>", unsafe_allow_html=True)

        st.markdown("---")

        # --- Charts ---
        st.subheader("Real-Time Trends")
        
        # Plotly chart for all parameters
        fig_all = go.Figure()
        for param in parameters:
            fig_all.add_trace(go.Scatter(x=df.index, y=df[param], mode='lines', name=param.title()))
        
        fig_all.update_layout(
            title_text='All Sensor Parameters Over Time',
            xaxis_title='Timestamp',
            yaxis_title='Value',
            legend_title='Parameter'
        )
        st.plotly_chart(fig_all, use_container_width=True)

        st.markdown("---")
        
        # Plotly chart for selected parameter with thresholds
        st.subheader(f"Historical Trend for {selected_parameter.title()}")
        fig_selected = go.Figure()
        fig_selected.add_trace(go.Scatter(x=df.index, y=df[selected_parameter], mode='lines', name=selected_parameter.title()))
        
        # Add threshold lines
        if selected_parameter == 'temperature':
            fig_selected.add_hline(y=60, line_dash="dash", line_color="orange", annotation_text="Warning Threshold", annotation_position="top left")
            fig_selected.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="Critical Threshold", annotation_position="top right")
        elif selected_parameter == 'pressure':
            fig_selected.add_hline(y=9, line_dash="dash", line_color="orange", annotation_text="Warning Threshold", annotation_position="top left")
            fig_selected.add_hline(y=12, line_dash="dash", line_color="red", annotation_text="Critical Threshold", annotation_position="top right")
        elif selected_parameter == 'vibration':
            fig_selected.add_hline(y=3, line_dash="dash", line_color="orange", annotation_text="Warning Threshold", annotation_position="top left")
            fig_selected.add_hline(y=5, line_dash="dash", line_color="red", annotation_text="Critical Threshold", annotation_position="top right")

        fig_selected.update_layout(
            title_text=f'Trend for {selected_parameter.title()}',
            xaxis_title='Timestamp',
            yaxis_title=selected_parameter.title(),
            showlegend=False
        )
        st.plotly_chart(fig_selected, use_container_width=True)

# ============================================================
# TAB 2: DATABASE (Expander)
# ============================================================
with tab2:
    st.subheader("Database Viewer")
    with st.expander("Click to view raw data"):
        if df.empty:
            st.warning("No records in database.")
        else:
            st.dataframe(df, use_container_width=True, height=500)

            # CSV Download
            csv = df.to_csv().encode("utf-8")
            st.download_button(
                "⬇️ Download CSV",
                csv,
                "air_compressor_data.csv",
                "text/csv",
                key="download-csv"
            )

# ============================================================
# AUTO REFRESH LOGIC
# ============================================================
time.sleep(5)
st.rerun()
