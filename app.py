# At top, import
from streamlit_autorefresh import st_autorefresh

# Inside Live Dashboard section (replace old code):

st_autorefresh(interval=5000, key="air_compressor_refresh")

live_df = get_live_data()

if live_df.empty:
    st.warning("⚠️ No data available. Please check your ESP32 connection.")
else:
    latest = live_df.iloc[-1]

    # Make 2 columns: Left for KPIs, Right for charts
    kpi_col, chart_col = st.columns([1, 3])

    with kpi_col:
        # Smaller KPIs stacked vertically with minimal padding
        for param in ["temperature", "pressure", "vibration"]:
            status, color = get_status(latest[param], param)
            st.markdown(
                f"""
                <div class="metric-container" style="padding:12px; margin-bottom:10px;">
                    <h4 style="margin:0;">{param.capitalize()}</h4>
                    <h2 style="margin:0;">{latest[param]:.2f}</h2>
                    <p class="status-text" style="color:{color}; margin:0;">{status}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with chart_col:
        st.markdown("### 📈 Historical Trends (Last 100 Readings)")
        chart_cols = st.columns(3)
        params = ["temperature", "pressure", "vibration"]
        colors = ["#00BFFF", "#88d8b0", "#6a5acd"]
        warns = [60, 9, 3]
        crits = [80, 12, 5]
        titles = ["Temperature Trend", "Pressure Trend", "Vibration Trend"]

        for i, col in enumerate(chart_cols):
            with col:
                st.plotly_chart(
                    create_chart(
                        live_df,
                        params[i],
                        titles[i],
                        colors[i],
                        warn_thresh=warns[i],
                        crit_thresh=crits[i],
                    ),
                    use_container_width=True,
                )

    st.info("✅ Dashboard refreshes every 5 seconds smoothly.")
