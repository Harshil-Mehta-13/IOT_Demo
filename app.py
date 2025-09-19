import streamlit as st
import pandas as pd
from supabase import create_client, Client
import time

# --- Page Configuration ---
st.set_page_config(
    page_title="Compressor IoT Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Supabase Connection ---
@st.cache_resource(ttl="30s") # Cache connection for 30 seconds
def init_connection():
    # Correctly access secrets using their variable names
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase_client = init_connection()

# --- Functions to Fetch Data ---
@st.cache_data(ttl="5s") # Cache data for 5 seconds to keep dashboard "live"
def get_sensor_data():
    try:
        response = supabase_client.table("air_compressor").select("*").order("timestamp", desc=True).limit(100).execute()
        data = response.data
        if not data:
            st.warning("No data found in the database. Please check your ESP32 connection.")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp").sort_index()
        return df

    except Exception as e:
        st.error(f"Error fetching data from Supabase: {e}")
        return pd.DataFrame()

# --- Dashboard Layout ---
st.title("Air Compressor Monitoring Dashboard ⚙️")
st.markdown("---")

df = get_sensor_data()

# --- Display Latest Values ---
if not df.empty:
    latest_data = df.iloc[-1]
    
    st.header("Latest Readings")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="Temperature (°C)", value=f"{latest_data['temperature']:.2f}")

    with col2:
        st.metric(label="Pressure (bar)", value=f"{latest_data['pressure']:.2f}")

    with col3:
        st.metric(label="Vibration", value=f"{latest_data['vibration']:.4f}")

    st.markdown("---")

# --- Display Historical Charts ---
st.header("Historical Trends")
if not df.empty:
    st.line_chart(df[['temperature', 'pressure', 'vibration']], use_container_width=True)
else:
    st.info("Waiting for data to arrive from the ESP32...")

# --- Auto-refresh logic ---
st.markdown("---")
st.write("Dashboard auto-refreshes every 5 seconds.")
time.sleep(5)
st.rerun() # This has been changed to st.rerun()
