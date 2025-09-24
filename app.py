if app_mode == "Live Dashboard":
    live_placeholder = st.empty()
    while True:
        live_df = get_live_data()

        # Filter last 1 hour data
        if not live_df.empty:
            now = live_df.index.max()
            last_hour_df = live_df[live_df.index >= (now - pd.Timedelta(hours=1))]
        else:
            last_hour_df = pd.DataFrame()

        with live_placeholder.container():
            if last_hour_df.empty:
                st.warning("No data available in the last 1 hour. Please check your ESP32 connection.")
            else:
                latest = last_hour_df.iloc[-1]

                # Layout: 2 columns → KPIs on right, Charts on left
                chart_col, kpi_col = st.columns([2, 1])

                with kpi_col:
                    st.subheader("Current Status")
                    st.metric(label="🌡️ Temp (°C)", value=f"{latest['temperature']:.2f}")
                    st.markdown(
                        f"**Status:** <span style='color: {get_status_color(latest['temperature'], 'temperature')};'>"
                        f"{get_status_text(latest['temperature'], 'temperature')}</span>",
                        unsafe_allow_html=True
                    )
                    st.metric(label="PSI Pressure (bar)", value=f"{latest['pressure']:.2f}")
                    st.markdown(
                        f"**Status:** <span style='color: {get_status_color(latest['pressure'], 'pressure')};'>"
                        f"{get_status_text(latest['pressure'], 'pressure')}</span>",
                        unsafe_allow_html=True
                    )
                    st.metric(label="📳 Vibration", value=f"{latest['vibration']:.2f}")
                    st.markdown(
                        f"**Status:** <span style='color: {get_status_color(latest['vibration'], 'vibration')};'>"
                        f"{get_status_text(latest['vibration'], 'vibration')}</span>",
                        unsafe_allow_html=True
                    )

                with chart_col:
                    st.subheader("Trends (Last 1 Hour)")
                    fig_temp = create_chart(last_hour_df, 'temperature', 'Temperature (°C)', '#00BFFF', 60, 80, height=250)
                    st.plotly_chart(fig_temp, use_container_width=True)

                    fig_pressure = create_chart(last_hour_df, 'pressure', 'Pressure (bar)', '#88d8b0', 9, 12, height=250)
                    st.plotly_chart(fig_pressure, use_container_width=True)

                    fig_vibration = create_chart(last_hour_df, 'vibration', 'Vibration', '#6a5acd', 3, 5, height=250)
                    st.plotly_chart(fig_vibration, use_container_width=True)

        time.sleep(5)
