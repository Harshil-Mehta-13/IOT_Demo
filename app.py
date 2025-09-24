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

                # Layout: KPIs first, Charts second
                kpi_col, chart_col = st.columns([1, 2])

                # ===== KPIs Column =====
                with kpi_col:
                    st.subheader("📊 Current Status")
                    st.metric(label="🌡️ Temp (°C)", value=f"{latest['temperature']:.2f}")
                    st.markdown(
                        f"**Status:** <span style='color: {get_status_color(latest['temperature'], 'temperature')};'>"
                        f"{get_status_text(latest['temperature'], 'temperature')}</span>",
                        unsafe_allow_html=True
                    )
                    st.metric(label="🛢️ Pressure (bar)", value=f"{latest['pressure']:.2f}")
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

                # ===== Charts Column =====
                with chart_col:
                    st.subheader("📈 Trends (Last 1 Hour)")

                    def styled_chart(df, y_col, title, color, low, high):
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=df.index,
                            y=df[y_col],
                            mode="lines+markers",
                            line=dict(color=color, width=3, shape="spline"),
                            marker=dict(size=6),
                            name=title
                        ))
                        # Thresholds
                        fig.add_hline(y=low, line_dash="dot", line_color="orange")
                        fig.add_hline(y=high, line_dash="dot", line_color="red")
                        # Layout style
                        fig.update_layout(
                            title=title,
                            title_x=0.5,
                            height=280,
                            margin=dict(l=10, r=10, t=30, b=10),
                            template="plotly_white",
                            xaxis=dict(showgrid=False),
                            yaxis=dict(showgrid=False),
                            hovermode="x unified",
                            plot_bgcolor="rgba(245,245,245,0.8)"
                        )
                        return fig

                    st.plotly_chart(
                        styled_chart(last_hour_df, "temperature", "🌡️ Temperature (°C)", "#00BFFF", 60, 80),
                        use_container_width=True
                    )

                    st.plotly_chart(
                        styled_chart(last_hour_df, "pressure", "🛢️ Pressure (bar)", "#88d8b0", 9, 12),
                        use_container_width=True
                    )

                    st.plotly_chart(
                        styled_chart(last_hour_df, "vibration", "📳 Vibration", "#6a5acd", 3, 5),
                        use_container_width=True
                    )

        time.sleep(5)
