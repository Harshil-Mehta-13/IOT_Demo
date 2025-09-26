import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# -------------------------------
# Simulated live data fetch
# Replace with DB query for real IoT data
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
# Main UI
# -------------------------------
st.set_page_config(layout="wide")
st.title("🌡️ IoT Live Dashboard")

data = get_live_data(100)
latest = data.iloc[-1]

# Layout: 2 columns
col1, col2 = st.columns([2, 1])

# Gauges in one row (left side)
with col1:
    g1, g2, g3 = st.columns(3)
    with g1:
        st.plotly_chart(create_gauge(latest["temperature"], "Temperature", 50, 100, "°C"), use_container_width=True)
    with g2:
        st.plotly_chart(create_gauge(latest["pressure"], "Pressure", 20, 40, "bar"), use_container_width=True)
    with g3:
        st.plotly_chart(create_gauge(latest["vibration"], "Vibration", 0, 10, "mm/s"), use_container_width=True)

# KPIs stacked vertically (right side)
with col2:
    kpi_card("Avg Temperature", data["temperature"].mean(), "°C")
    kpi_card("Avg Pressure", data["pressure"].mean(), "bar")
    kpi_card("Avg Vibration", data["vibration"].mean(), "mm/s")
