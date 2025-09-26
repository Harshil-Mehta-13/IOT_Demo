import streamlit as st
import pandas as pd
from supabase import create_client
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
import pytz
from datetime import datetime, timedelta

# --- Config & Styling ---
st.set_page_config(page_title="Air Compressor Dashboard", page_icon="⚙️", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
#MainMenu, footer, header {visibility: hidden;}
.status-badge {
    font-weight: 700; border-radius: 12px; padding: 2px 8px; font-size: 11px; display: inline-block; color: white;
}
.status-normal {background-color: #2ec27e;}
.status-warning {background-color: #ffcc00; color: black;}
.status-critical {background-color: #ff4b4b;}
.sidebar-title {
    font-weight: bold; font-size: 18px; margin-bottom: 10px;
    padding: 8px 12px; border-radius: 6px;
    background: linear-gradient(to right, #2c5364, #203a43, #0f2027); color:white;
}
</style>
""", unsafe_allow_html=True)

# --- Supabase Setup ---
@st.cache_resource(ttl=30)
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
supabase_client = init_supabase()

STATUS_THRESHOLDS = {
    "temperature": {"warn": 60, "crit": 80, "range": [0, 100]},
    "pressure": {"warn": 9, "crit": 12, "range": [0, 15]},
    "vibration": {"warn": 3, "crit": 5, "range": [0, 8]},
}
STATUS_COLORS = {"normal":"#2ec27e", "warning":"#ffcc00", "critical":"#ff4b4b"}

# --- Helpers ---
def get_status(val, param):
    key = param.lower()
    if key not in STATUS_THRESHOLDS or pd.isna(val):
        return "normal"
    t = STATUS_THRESHOLDS[key]
    if val > t["crit"]: return "critical"
    elif val > t["warn"]: return "warning"
    return "normal"

def create_gauge(value, param, height=220, font_size=22):
    key = param.lower()
    if key not in STATUS_THRESHOLDS: return go.Figure()
    t = STATUS_THRESHOLDS[key]
    status = get_status(value, key)
    color = STATUS_COLORS[status]
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=(0 if pd.isna(value) else value),
        number={'font': {'size': font_size, 'color': color}, 'valueformat': '.2f'},
        title={'text': param.capitalize(), 'font': {'size': 16}},
        gauge={
            'axis': {'range': t["range"], 'tickcolor': "darkgray"},
            'bar': {'color': color, 'thickness': 0.35},
            'steps': [
                {'range': [t["range"][0], t["warn"]], 'color': "#e6f7ec"},
                {'range': [t["warn"], t["crit"]], 'color': "#fff0d9"},
                {'range': [t["crit"], t["range"][1]], 'color': "#ffe6e9"},
            ],
            'threshold': {'line': {'color': "red", 'width': 3}, 'value': t["crit"]}
        }
    ))
    fig.update_layout(height=height, margin=dict(t=30, b=20, l=20, r=20), template="plotly_white")
    return fig

def create_trend_chart(df, param):
    t = STATUS_THRESHOLDS[param]
    status_color = STATUS_COLORS[get_status(df[param].iloc[-1], param)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df[param], mode="lines", line=dict(width=2.5, color=status_color)))
    fig.add_hline(y=t["warn"], line_dash="dash", line_color="orange", annotation_text="Warning", annotation_position="bottom right")
    fig.add_hline(y=t["crit"], line_dash="dash", line_color="red", annotation_text="Critical", annotation_position="bottom right")
    fig.update_layout(title=f"{param.capitalize()} Trend (Last 120 readings)", height=250, margin=dict(l=30,r=30,t=40,b=30),
                      template="plotly_white", yaxis=dict(range=t["range"]), showlegend=False, title_x=0.5)
    return fig

def fetch_data():
    try:
        resp = supabase_client.table("air_compressor").select("*").order("timestamp", desc=True).limit(120).execute()
        if not resp.data: return pd.DataFrame()
        df = pd.DataFrame(resp.data)
        ist = pytz.timezone('Asia/Kolkata')
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert(ist)
        return df.set_index("timestamp").sort_index()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# --- Sidebar ---
with st.sidebar:
    st.markdown("<div class='sidebar-title'>Navigation</div>", unsafe_allow_html=True)
    app_mode = st.radio("View Mode", ["Live Dashboard", "Database"])

# --- Title ---
st.title("⚙️ Air Compressor Monitoring Dashboard")

# --- Main ---
data = fetch_data()
if app_mode == "Live Dashboard":
    st_autorefresh(interval=5000, key="dashboard_refresh")

    if data.empty:
        st.warning("No data available to display.")
    else:
        latest = data.iloc[-1]
        
        # Create two main columns: one for gauges, one for charts
        col_gauges, col_charts = st.columns([1, 2])

        with col_gauges:
            for p in ["temperature", "pressure", "vibration"]:
                st.plotly_chart(create_gauge(latest[p], p), use_container_width=True)

        with col_charts:
            for p in ["temperature", "pressure", "vibration"]:
                st.plotly_chart(create_trend_chart(data, p), use_container_width=True)


elif app_mode == "Database":
    st.subheader("Explore Raw Data")
    start_col, end_col, param_col = st.columns(3)
    with start_col: start_date = st.date_input("Start Date", datetime.now().date()-timedelta(days=7))
    with end_col: end_date = st.date_input("End Date", datetime.now().date())
    with param_col: selected_params = st.multiselect("Select Parameter(s):", ["temperature","pressure","vibration"], default=["temperature","pressure","vibration"])
    try:
        ist = pytz.timezone("Asia/Kolkata")
        start_dt, end_dt = datetime.combine(start_date, datetime.min.time()), datetime.combine(end_date, datetime.max.time())
        start_utc, end_utc = ist.localize(start_dt).astimezone(pytz.utc), ist.localize(end_dt).astimezone(pytz.utc)
        resp = supabase_client.table("air_compressor").select("*").gte("timestamp", start_utc.isoformat()).lte("timestamp", end_utc.isoformat()).execute()
        df = pd.DataFrame(resp.data)
        if df.empty:
            st.warning("No data found in selected range.")
        else:
            if selected_params: df = df[["timestamp"]+selected_params]
            st.dataframe(df, use_container_width=True, height=500)
            st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), "filtered_data.csv", "text/csv", key="download")
    except Exception as e:
        st.error(f"Error fetching data: {e}")
