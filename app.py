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
.metric-container {
    background: #fff;
    border-radius: 8px;
    padding: 8px 15px;
    margin: 6px 0;
    color: #222;
    border: 1px solid #ecf1f7;
    box-shadow: 0 2px 8px rgba(39,121,226,0.06);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    min-width:100px;
}
.metric-title {font-size: 13px; font-weight: 600;}
.metric-value {font-size: 20px; font-weight: 700;}
.sidebar-title {
    font-weight: bold; font-size: 18px; margin-bottom: 10px;
    padding: 8px 12px; border-radius: 6px;
    background: linear-gradient(to right, #e3ecfa, #f3f7fb); color:#2779e2;
    border-left: 5px solid #2779e2;
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

def get_status(val, param):
    key = param.lower()
    if key not in STATUS_THRESHOLDS or pd.isna(val):
        return "normal"
    t = STATUS_THRESHOLDS[key]
    if val > t["crit"]: return "critical"
    elif val > t["warn"]: return "warning"
    return "normal"

def render_kpi(param, value):
    status = get_status(value, param)
    status_class = f"status-{status}"
    val_str = "N/A" if pd.isna(value) else f"{value:.2f}"
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-title">{param.capitalize()}</div>
        <div style="display:flex; gap:8px; align-items:center; justify-content:center;">
            <div class="metric-value">{val_str}</div>
            <div class="status-badge {status_class}">{status.capitalize()}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- Improved Professional Gauge (Light) ---
def create_gauge(value, param, height=220, font_size=22):
    key = param.lower()
    if key not in STATUS_THRESHOLDS: return go.Figure()
    t = STATUS_THRESHOLDS[key]
    status = get_status(value, key)
    color = STATUS_COLORS[status]
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=(0 if pd.isna(value) else value),
        number={'font': {'size': font_size+4, 'color': color, 'family': 'Segoe UI, Verdana, Geneva, Tahoma, sans-serif'}},
        title={'text': param.capitalize(), 'font': {'size': 14, 'color': '#555'}},
        gauge={
            'axis': {'range': t["range"], 'tickcolor': "#bbb", 'tickwidth': 1.5, 'ticklen': 7},
            'bgcolor': "white",
            'bar': {'color': color, 'thickness': 0.1},
            'borderwidth': 0,
            'steps': [
                {'range': [t["range"][0], t["warn"]], 'color': "rgba(44,201,126, 0.10)"},    # softer green
                {'range': [t["warn"], t["crit"]], 'color': "rgba(255,204,0, 0.12)"},         # soft yellow
                {'range': [t["crit"], t["range"][1]], 'color': "rgba(255,75,75, 0.12)"},     # soft red
            ],
            'threshold': {
                'line': {'color': "#e74c3c", 'width': 3.5},
                'value': t["crit"],
                'thickness': 0.7
            }
        }
    ))
    fig.update_layout(
        height=height,
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI, Verdana, Geneva, Tahoma, sans-serif"),
        margin=dict(t=18, b=10, l=10, r=10),
    )
    return fig

def create_trend_chart(df, param):
    t = STATUS_THRESHOLDS[param]
    status_color = STATUS_COLORS[get_status(df[param].iloc[-1], param)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df[param], mode="lines", line=dict(width=2.5, color=status_color)))
    fig.add_hline(y=t["warn"], line_dash="dash", line_color="orange")
    fig.add_hline(y=t["crit"], line_dash="dash", line_color="red")
    fig.update_layout(title=f"{param.capitalize()} Trend", height=350,
        margin=dict(l=30,r=30,t=40,b=30),
        template="plotly_white",
        yaxis=dict(range=t["range"]),
        showlegend=False, 
        title_x=0.5
    )
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
        st.warning("No data available. Showing last 100 entries if available.")
        data = fetch_data().tail(100)

    if not data.empty:
        latest = data.iloc[-1]
        col_kpis, col_gauges = st.columns([1,3])

        # KPIs on left
        with col_kpis:
            for p in ["temperature","pressure","vibration"]:
                render_kpi(p, latest[p])

        # Gauges on right
        with col_gauges:
            row = st.columns(3)
            for i,p in enumerate(["temperature","pressure","vibration"]):
                with row[i]:
                    st.plotly_chart(create_gauge(latest[p], p), use_container_width=True)

        # Trend charts stacked
        for p in ["temperature","pressure","vibration"]:
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
