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

# --- Main App Logic ---
st.title("Air Compressor Monitoring ⚙️")

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

        # --- KPI Metrics ---
        st.subheader("Latest Readings")
        kpi1, kpi2, kpi3 = st.columns(3)

        # Temperature KPI
        temp_color = "🔴" if latest["temperature"] > 80 else ("🟠" if latest["temperature"] > 60 else "🟢")
        kpi1.metric("Temperature (°C)", f"{latest['temperature']:.2f}")
        kpi1.markdown(f"**{temp_color} Status**")

        # Pressure KPI
        pressure_color = "🔴" if latest["pressure"] > 12 else ("🟠" if latest["pressure"] > 9 else "🟢")
        kpi2.metric("Pressure (bar)", f"{latest['pressure']:.2f}")
        kpi2.markdown(f"**{pressure_color} Status**")

        # Vibration KPI
        vib_color = "🔴" if latest["vibration"] > 5 else ("🟠" if latest["vibration"] > 3 else "🟢")
        kpi3.metric("Vibration", f"{latest['vibration']:.2f}")
        kpi3.markdown(f"**{vib_color} Status**")

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
        
        # Plotly chart for selected parameter
        st.subheader(f"Historical Trend for {selected_parameter.title()}")
        fig_selected = go.Figure()
        fig_selected.add_trace(go.Scatter(x=df.index, y=df[selected_parameter], mode='lines'))
        
        fig_selected.update_layout(
            title_text=f'Trend for {selected_parameter.title()}',
            xaxis_title='Timestamp',
            yaxis_title=selected_parameter.title()
        )
        st.plotly_chart(fig_selected, use_container_width=True)
        
        # --- Insights ---
        st.markdown("---")
        st.subheader("Insights")
        avg_temp = df["temperature"].mean()
        avg_pressure = df["pressure"].mean()
        avg_vibration = df["vibration"].mean()

        st.info(
            f"📌 Average Temperature: **{avg_temp:.2f}°C** | "
            f"Average Pressure: **{avg_pressure:.2f} bar** | "
            f"Average Vibration: **{avg_vibration:.2f}**"
        )

# ============================================================
# TAB 2: DATABASE
# ============================================================
with tab2:
    st.subheader("Database Viewer")
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
