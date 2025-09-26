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
.metric-container {
    background-color: #fff;
    border-radius: 8px;
    padding: 8px 15px;
    margin: 6px 0;
    color: #222;
    border: 1px solid #ecf1f7;
    box-shadow: 0 2px 8px rgba(39,121,226,0.06);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    min-width:100px;
}
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
STATUS_TEXT = {"normal":"Normal", "warning":"Warning", "critical":"Critical"}

def get_status(val, param):
    key = param.lower()
    if key not in STATUS_THRESHOLDS or pd.isna(val):
        return "normal"
    t = STATUS_THRESHOLDS[key]
    if val > t["crit"]:
        return "critical"
    elif val > t["warn"]:
        return "warning"
    return "normal"

def create_gauge(value, param, height=230):
    key = param.lower()
    if key not in STATUS_THRESHOLDS: return go.Figure()
    t = STATUS_THRESHOLDS[key]
    status = get_status(value, key)
    color = STATUS_COLORS[status]
    status_text = STATUS_TEXT[status]
    val_display = 0 if pd.isna(value) else value

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=val_display,
        number={'font': {'size': 46, 'color': color,
                         'family': 'Segoe UI, Verdana, Geneva, Tahoma, sans-serif'},
                'suffix': f"<br><span style='font-size:16px;color:#555;font-weight:600'>{status_text}</span>",
                'valueformat':".2f"},
        title={'text': f"<b>{param.capitalize()}</b>", 'font': {'size': 18, 'color': '#334e68'}},
        gauge={
            'axis': {'range': t["range"], 'tickcolor': "#777", 'showline': True, 'linecolor': '#ddd', 'linewidth': 2},
            'bgcolor': "#f7fafc",
            'borderwidth': 0,
            'bar': {'color': color, 'thickness': 0.15},
            'steps': [
                {'range': [t["range"][0], t["warn"]], 'color': "rgba(45,206,137,0.18)"},
                {'range': [t["warn"], t["crit"]], 'color': "rgba(240,173,78,0.18)"},
                {'range': [t["crit"], t["range"][1]], 'color': "rgba(229,83,83,0.18)"},
            ],
            'threshold': {'line': {'color': "#cc3f3f", 'width': 5}, 'value': t["crit"], 'thickness': 0.7}
        }
    ))
    fig.update_layout(
        height=height,
        margin=dict(t=30, b=10, l=10, r=10),
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        font={'family': 'Segoe UI, Verdana, Geneva, Tahoma, sans-serif'},
    )
    return fig

def create_trend_chart(df, param):
    t = STATUS_THRESHOLDS[param]
    status_color = STATUS_COLORS[get_status(df[param].iloc[-1], param)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df[param], mode="lines", line=dict(width=3, color=status_color), hoverinfo="x+y"))
    fig.add_hline(y=t["warn"], line_dash="dash", line_color="#f0ad4e", annotation_text="Warning", annotation_font=dict(size=12), annotation_position="top left")
    fig.add_hline(y=t["crit"], line_dash="dash", line_color="#e55353", annotation_text="Critical", annotation_font=dict(size=12), annotation_position="top left")
    fig.update_layout(
        title=f"{param.capitalize()} Trend",
        height=350,
        margin=dict(l=50, r=50, t=50, b=30),
        template="plotly_white",
        yaxis=dict(range=t["range"], gridcolor="#e2e8f0", zerolinecolor="#cbd5e1"),
        xaxis_title="Time",
        showlegend=False,
        title_x=0.5,
        hovermode="x unified"
    )
    return fig

def fetch_data():
    try:
        resp = supabase_client.table("air_compressor").select("*").order("timestamp", desc=True).limit(120).execute()
        if not resp.data:
            return pd.DataFrame()
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
        st.warning("No data available. Please check your ESP32 connection.")
    else:
        latest = data.iloc[-1]

        col_gauges, col_charts = st.columns([1, 3])

        with col_gauges:
            for param in ["temperature", "pressure", "vibration"]:
                st.plotly_chart(create_gauge(latest[param], param), use_container_width=True)

        with col_charts:
            for param in ["temperature", "pressure", "vibration"]:
                st.plotly_chart(create_trend_chart(data, param), use_container_width=True)

elif app_mode == "Database":
    st.subheader("Explore Raw Data")
    start_col, end_col, param_col = st.columns(3)
    with start_col:
        start_date = st.date_input("Start Date", datetime.now().date() - timedelta(days=7))
    with end_col:
        end_date = st.date_input("End Date", datetime.now().date())
    with param_col:
        selected_params = st.multiselect("Select Parameter(s):", ["temperature", "pressure", "vibration"], default=["temperature", "pressure", "vibration"])

    try:
        ist = pytz.timezone("Asia/Kolkata")
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        start_utc = ist.localize(start_dt).astimezone(pytz.utc)
        end_utc = ist.localize(end_dt).astimezone(pytz.utc)

        resp = supabase_client.table("air_compressor").select("*").gte("timestamp", start_utc.isoformat()).lte("timestamp", end_utc.isoformat()).execute()
        df = pd.DataFrame(resp.data)
        if df.empty:
            st.warning("No data found in selected range.")
        else:
            if selected_params:
                df = df[["timestamp"] + selected_params]
            st.dataframe(df, use_container_width=True, height=500)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV", csv, "filtered_data.csv", "text/csv", key="download")
    except Exception as e:
        st.error(f"Error fetching data: {e}")
