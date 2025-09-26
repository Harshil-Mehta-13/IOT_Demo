import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# -------------------------------
# Simulated live data fetch
# Replace with your Supabase query
# -------------------------------
def get_live_data(n=100):
    timestamp = pd.date_range(end=pd.Timestamp.now(), periods=n, freq="T")
    data = pd.DataFrame({
        "timestamp": timestamp,
        "temperature": np.random.normal(70, 5, n),
        "pressure": np.random.normal(30, 3, n),
        "vibration": np.random.normal(5, 1, n)
    })
    return data

# -------------------------------
# Gauge chart (Plotly)
# -------------------------------
def create_gauge(value, title, min_val, max_val, unit):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': f"{title} ({unit})"},
        gauge={
            'axis': {'range': [min_val, max_val]},
            'bar': {'color': "royalblue"},
            'borderwidth': 2,
            'bordercolor': "gray",
        }
    ))
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=10))
    return fig

# -------------------------------
# KPI Card (styled with HTML/CSS)
# -------------------------------
def kpi_card(title, value, unit):
    st.markdown(
        f"""
        <div style="
            background-color:#f9f9f9;
            padding:20px;
            border-radius:15px;
            text-align:center;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
            height: 150px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            margin-bottom: 15px;
        ">
            <h4 style="margin:0; color:#555;">{title}</h4>
            <h2 style="margin:0; color:#111;">{value:.2f} {unit}</h2>
        </div>
        """,
        unsafe_allow_html=True
    )

# -------------------------------
# Main App
# -------------------------------
st.set_page_config(page_title="IoT Dashboard", layout="wide")
st.title("🌡️ IoT Live Dashboard")

# Fetch Data
data = get_live_data(100)  # Replace with Supabase fetch
latest = data.iloc[-1]

# -------------------------------
# Layout: Gauges + KPIs
# -------------------------------
col1, col2 = st.columns([2, 1])

# Gauges row (left)
with col1:
    g1, g2, g3 = st.columns(3)
    with g1:
        st.plotly_chart(create_gauge(latest["temperature"], "Temperature", 50, 100, "°C"), use_container_width=True)
    with g2:
        st.plotly_chart(create_gauge(latest["pressure"], "Pressure", 20, 40, "bar"), use_container_width=True)
    with g3:
        st.plotly_chart(create_gauge(latest["vibration"], "Vibration", 0, 10, "mm/s"), use_container_width=True)

# KPIs stacked vertically (right)
with col2:
    kpi_card("Avg Temperature", data["temperature"].mean(), "°C")
    kpi_card("Avg Pressure", data["pressure"].mean(), "bar")
    kpi_card("Avg Vibration", data["vibration"].mean(), "mm/s")

# -------------------------------
# Trend Charts (last 100 entries)
# -------------------------------
st.subheader("📊 Trends (Last 100 readings)")

c1, c2, c3 = st.columns(3)

with c1:
    fig_temp = px.line(data, x="timestamp", y="temperature", title="Temperature Trend", markers=True)
    fig_temp.update_layout(height=300, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_temp, use_container_width=True)

with c2:
    fig_press = px.line(data, x="timestamp", y="pressure", title="Pressure Trend", markers=True)
    fig_press.update_layout(height=300, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_press, use_container_width=True)

with c3:
    fig_vib = px.line(data, x="timestamp", y="vibration", title="Vibration Trend", markers=True)
    fig_vib.update_layout(height=300, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_vib, use_container_width=True)
