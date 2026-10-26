import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from cot_data import (
    get_cot_data,
    get_market_summary,
    get_cot_regime,
    get_multitimeframe_changes,
    get_multitimeframe_context,
    generate_cot_summary
)

st.set_page_config(
    page_title="COT Analyzer",
    layout="wide"
)

st.title("COT Analyzer")

st.write("Institutional positioning analysis")

market = st.selectbox(
    "Market",
    [
        "S&P 500",
        "NASDAQ-100",
        "NIKKEI 225"
    ]
)

st.write("Selected market:", market)

def get_direction_color(direction):

    if "Bullish" in direction:
        return "#2ECC71"

    elif "Bearish" in direction:
        return "#E74C3C"

    else:
        return "#F1C40F"


try:

    
    df = get_cot_data(market)

    latest = df.iloc[-1]
    summary = get_market_summary(df)

    multitimeframe_changes = get_multitimeframe_changes(df)

    multitimeframe_context = get_multitimeframe_context(
    multitimeframe_changes
    )

    regime = get_cot_regime(
        summary,
        multitimeframe_context
    )

    cot_summary = generate_cot_summary(
    regime,
    multitimeframe_context
    )

    report_date = latest[
        "report_date_as_yyyy_mm_dd"
    ].strftime("%B %d, %Y")

    st.success(
        f"Latest COT Report: {report_date}"
    )

    st.subheader("Institutional Positioning")

# =========================
# COT REGIME
# =========================

    st.subheader("COT Regime")

    st.markdown(
        f"### {regime['regime']}"
    )

    regime_metric_col1, regime_metric_col2 = st.columns(2)

    with regime_metric_col1:
        st.metric(
            "Flow Intensity",
            f"{regime['regime_confidence']} "
            f"({regime['regime_strength']:.1f}%)"
        )

    with regime_metric_col2:
        st.metric(
            "Regime Confirmation",
            f"{regime['confirmation_label']} "
            f"({regime['confirmation_score']:.1f}%)"
        )

    # =========================
    # REGIME CONFIRMATION
    # =========================

    confirmation_col1, confirmation_col2 = st.columns(2)

    with confirmation_col1:
        st.write("**Asset Manager MTF Confirmation**")
        st.write(
            f"{regime['asset_mtf_score']}/3 — "
            f"**{regime['asset_mtf_status']}**"
        )

    with confirmation_col2:
        st.write("**Leveraged Funds MTF Confirmation**")
        st.write(
            f"{regime['leveraged_mtf_score']}/3 — "
            f"**{regime['leveraged_mtf_status']}**"
        )

    regime_col1, regime_col2, regime_col3 = st.columns(3)

# =========================
# ASSET MANAGER
# =========================

    with regime_col1:
        st.markdown("#### Asset Manager")

        asset_direction_color = get_direction_color(
    regime["asset_direction"]
)

        st.markdown(
            f"""
            Direction:
            <span style="color:{asset_direction_color}; font-weight:700;">
            {regime["asset_direction"]}
            </span>
            """,
            unsafe_allow_html=True
        )

        st.write(
            f"Flow Type: **{regime['asset_flow_type']}**"
        )

        st.write(
            f"Flow: **{regime['asset_flow']}**"
        )

        st.write(
            f"Strength: **{regime['asset_strength']}** "
            f"({regime['asset_strength_percentile']:.1f}%)"
        )

        st.caption(
            regime["asset_positioning"]
        )


# =========================
# LEVERAGED FUNDS
# =========================

    with regime_col2:
        st.markdown("#### Leveraged Funds")

        leveraged_direction_color = get_direction_color(
    regime["leveraged_direction"]
)

        st.markdown(
            f"""
            Direction:
            <span style="color:{leveraged_direction_color}; font-weight:700;">
                {regime["leveraged_direction"]}
            </span>
            """,
            unsafe_allow_html=True
        )

        st.write(
            f"Flow Type: **{regime['leveraged_flow_type']}**"
        )

        st.write(
            f"Flow: **{regime['leveraged_flow']}**"
        )

        st.write(
            f"Strength: **{regime['leveraged_strength']}** "
            f"({regime['leveraged_strength_percentile']:.1f}%)"
        )

        st.caption(
            regime["leveraged_positioning"]
        )


# =========================
# DEALER
# =========================

    with regime_col3:
        st.markdown("#### Dealer Context")

        dealer_direction_color = get_direction_color(
    regime["dealer_direction"]
)

        st.markdown(
            f"""
            Direction:
            <span style="color:{dealer_direction_color}; font-weight:700;">
                {regime["dealer_direction"]}
            </span>
            """,
            unsafe_allow_html=True
        )

        st.write(
            f"Flow Type: **{regime['dealer_flow_type']}**"
        )

        st.write(
            f"Flow: **{regime['dealer_flow']}**"
        )

        st.write(
            f"Strength: **{regime['dealer_strength']}** "
            f"({regime['dealer_strength_percentile']:.1f}%)"
        )

        st.caption(
            regime["dealer_positioning"]
        )

    if regime["divergence"] != "None":
        st.info(
            f"Divergence: {regime['divergence']}"
        )

    # =========================
    # MULTI-TIMEFRAME CONTEXT
    # =========================

    st.markdown("### Multi-Timeframe Context")

    mtf_col1, mtf_col2, mtf_col3 = st.columns(3)

    # Short-Term
    with mtf_col1:
        st.markdown("#### Short-Term")

        asset_short = multitimeframe_context["asset_short_term"]
        asset_short_color = get_direction_color(asset_short)

        st.markdown(
            f"""
            Asset Manager:
            <span style="color:{asset_short_color}; font-weight:700;">
                {asset_short}
            </span>
            """,
            unsafe_allow_html=True
        )

        leveraged_short = multitimeframe_context["leveraged_short_term"]
        leveraged_short_color = get_direction_color(leveraged_short)

        st.markdown(
            f"""
            Leveraged Funds:
            <span style="color:{leveraged_short_color}; font-weight:700;">
                {leveraged_short}
            </span>
            """,
            unsafe_allow_html=True
        )

        st.write("---")

        asset_trend = multitimeframe_context["asset_trend_state"]
        asset_trend_color = get_direction_color(asset_trend)

        st.markdown(
            f"""
            Asset Trend:
            <span style="color:{asset_trend_color}; font-weight:700;">
                {asset_trend}
            </span>
            """,
            unsafe_allow_html=True
        )

        leveraged_trend = multitimeframe_context["leveraged_trend_state"]
        leveraged_trend_color = get_direction_color(leveraged_trend)

        st.markdown(
            f"""
            Leveraged Trend:
            <span style="color:{leveraged_trend_color}; font-weight:700;">
                {leveraged_trend}
            </span>
            """,
            unsafe_allow_html=True
        )

    # Medium-Term
    with mtf_col2:
        st.markdown("#### Medium-Term")

        asset_medium = multitimeframe_context["asset_medium_term"]
        asset_medium_color = get_direction_color(asset_medium)

        st.markdown(
            f"""
            Asset Manager:
            <span style="color:{asset_medium_color}; font-weight:700;">
                {asset_medium}
            </span>
            """,
            unsafe_allow_html=True
        )

        leveraged_medium = multitimeframe_context["leveraged_medium_term"]
        leveraged_medium_color = get_direction_color(leveraged_medium)

        st.markdown(
            f"""
            Leveraged Funds:
            <span style="color:{leveraged_medium_color}; font-weight:700;">
                {leveraged_medium}
            </span>
            """,
            unsafe_allow_html=True
        )

    # Long-Term
    with mtf_col3:
        st.markdown("#### Long-Term")

        asset_long = multitimeframe_context["asset_long_term"]
        asset_long_color = get_direction_color(asset_long)

        st.markdown(
            f"""
            Asset Manager:
            <span style="color:{asset_long_color}; font-weight:700;">
                {asset_long}
            </span>
            """,
            unsafe_allow_html=True
        )

        leveraged_long = multitimeframe_context["leveraged_long_term"]
        leveraged_long_color = get_direction_color(leveraged_long)

        st.markdown(
            f"""
            Leveraged Funds:
            <span style="color:{leveraged_long_color}; font-weight:700;">
                {leveraged_long}
            </span>
            """,
            unsafe_allow_html=True
        )

    # =========================
    # COT ANALYSIS SUMMARY
    # =========================

    st.markdown("### COT Analysis Summary")

    st.write(
        cot_summary["asset_summary"]
    )

    st.write(
        cot_summary["leveraged_summary"]
    )

    st.write(
        cot_summary["historical_summary"]
    )

    st.caption(
        cot_summary["dealer_summary"]
    )

    st.write("---")

    col1, col2, col3 = st.columns(3)

    # =========================
    # DEALER
    # =========================

    with col1:

        dealer = summary["Dealer"]

        st.markdown("### Dealer")

        st.metric(
            "Net Position",
            f"{dealer['net']:+,.0f}",
            f"{dealer['weekly_change']:+,.0f} 1W"
        )

        st.write(
            f"3Y Percentile: **{dealer['percentile']:.1f}%**"
        )

        st.write(
            f"Z-Score: **{dealer['zscore']:+.2f}**"
        )

        st.caption(
            f"State: {dealer['net_state']}"
        )

        st.write("---")

        # Long
        st.write(
            f"Long: **{dealer['long']:,.0f}** "
            f"({dealer['long_weekly_change']:+,.0f} 1W)"
        )

        st.caption(
            f"3Y Percentile: {dealer['long_percentile']:.1f}% "
            f"| Z-Score: {dealer['long_zscore']:+.2f} "
            f"| State: {dealer['long_state']}"
        )

        # Short
        st.write(
            f"Short: **{dealer['short']:,.0f}** "
            f"({dealer['short_weekly_change']:+,.0f} 1W)"
        )

        st.caption(
            f"3Y Percentile: {dealer['short_percentile']:.1f}% "
            f"| Z-Score: {dealer['short_zscore']:+.2f} "
            f"| State: {dealer['short_state']}"
        )

        # Long / Short Ratio
        if dealer["long_short_ratio"] is not None:
            st.write(
                f"Long / Short Ratio: "
                f"**{dealer['long_short_ratio']:.2f}x**"
            )
        else:
            st.write(
                "Long / Short Ratio: **N/A**"
            )

        # Direction
        st.write(
            f"Direction: **{dealer['direction']}**"
        )

        # Strength
        st.write(
            f"Strength: **{dealer['strength']}** "
            f"({dealer['strength_percentile']:.1f}%)"
        )

        # Positioning
        st.write(
            f"Positioning: "
            f"**{dealer['positioning_signal']}**"
        )


    # =========================
    # ASSET MANAGER
    # =========================

    with col2:

        asset = summary["Asset Manager"]

        st.markdown("### Asset Manager")

        st.metric(
            "Net Position",
            f"{asset['net']:+,.0f}",
            f"{asset['weekly_change']:+,.0f} 1W"
        )

        st.write(
            f"3Y Percentile: **{asset['percentile']:.1f}%**"
        )

        st.write(
            f"Z-Score: **{asset['zscore']:+.2f}**"
        )

        st.caption(
            f"State: {asset['net_state']}"
        )

        st.write("---")

        # Long
        st.write(
            f"Long: **{asset['long']:,.0f}** "
            f"({asset['long_weekly_change']:+,.0f} 1W)"
        )

        st.caption(
            f"3Y Percentile: {asset['long_percentile']:.1f}% "
            f"| Z-Score: {asset['long_zscore']:+.2f} "
            f"| State: {asset['long_state']}"
        )

        # Short
        st.write(
            f"Short: **{asset['short']:,.0f}** "
            f"({asset['short_weekly_change']:+,.0f} 1W)"
        )

        st.caption(
            f"3Y Percentile: {asset['short_percentile']:.1f}% "
            f"| Z-Score: {asset['short_zscore']:+.2f} "
            f"| State: {asset['short_state']}"
        )

        # Long / Short Ratio
        if asset["long_short_ratio"] is not None:
            st.write(
                f"Long / Short Ratio: "
                f"**{asset['long_short_ratio']:.2f}x**"
            )
        else:
            st.write(
                "Long / Short Ratio: **N/A**"
            )

        # Direction
        st.write(
            f"Direction: **{asset['direction']}**"
        )

        # Strength
        st.write(
            f"Strength: **{asset['strength']}** "
            f"({asset['strength_percentile']:.1f}%)"
        )

        # Positioning
        st.write(
            f"Positioning: "
            f"**{asset['positioning_signal']}**"
        )


    # =========================
    # LEVERAGED FUNDS
    # =========================

    with col3:

        leveraged = summary["Leveraged Funds"]

        st.markdown("### Leveraged Funds")

        st.metric(
            "Net Position",
            f"{leveraged['net']:+,.0f}",
            f"{leveraged['weekly_change']:+,.0f} 1W"
        )

        st.write(
            f"3Y Percentile: **{leveraged['percentile']:.1f}%**"
        )

        st.write(
            f"Z-Score: **{leveraged['zscore']:+.2f}**"
        )

        st.caption(
            f"State: {leveraged['net_state']}"
        )

        st.write("---")

        # Long
        st.write(
            f"Long: **{leveraged['long']:,.0f}** "
            f"({leveraged['long_weekly_change']:+,.0f} 1W)"
        )

        st.caption(
            f"3Y Percentile: {leveraged['long_percentile']:.1f}% "
            f"| Z-Score: {leveraged['long_zscore']:+.2f} "
            f"| State: {leveraged['long_state']}"
        )

        # Short
        st.write(
            f"Short: **{leveraged['short']:,.0f}** "
            f"({leveraged['short_weekly_change']:+,.0f} 1W)"
        )

        st.caption(
            f"3Y Percentile: {leveraged['short_percentile']:.1f}% "
            f"| Z-Score: {leveraged['short_zscore']:+.2f} "
            f"| State: {leveraged['short_state']}"
        )

        # Long / Short Ratio
        if leveraged["long_short_ratio"] is not None:
            st.write(
                f"Long / Short Ratio: "
                f"**{leveraged['long_short_ratio']:.2f}x**"
            )
        else:
            st.write(
                "Long / Short Ratio: **N/A**"
            )

        # Direction
        st.write(
            f"Direction: **{leveraged['direction']}**"
        )

        # Strength
        st.write(
            f"Strength: **{leveraged['strength']}** "
            f"({leveraged['strength_percentile']:.1f}%)"
        )

        # Positioning
        st.write(
            f"Positioning: "
            f"**{leveraged['positioning_signal']}**"
        )
    
    # =========================
    # MULTI-TIMEFRAME POSITIONING
    # =========================

    st.divider()

    st.subheader("Multi-Timeframe Positioning")

    timeframe_data = get_multitimeframe_changes(df)

    periods = ["1W", "1M", "3M", "6M", "1Y", "3Y"]

    # ==========================================
    # BUILD MULTI-TIMEFRAME TABLE
    # ==========================================

    table_rows = []

    for group_name, positions in timeframe_data.items():

        for position_type in ["Long", "Short", "Net"]:

            row = {
                "Participant": group_name,
                "Type": position_type
            }

            changes = positions[position_type]

            for period in periods:

                value = changes[period]

                if value is None:
                    row[period] = "N/A"
                else:
                    row[period] = f"{value:+,.0f}"

            table_rows.append(row)

    # ==========================================
    # CREATE DATAFRAME
    # ==========================================

    timeframe_table = pd.DataFrame(table_rows)

    timeframe_table = timeframe_table[
        [
            "Participant",
            "Type",
            "1W",
            "1M",
            "3M",
            "6M",
            "1Y",
            "3Y"
        ]
    ]

    # ==========================================
    # DISPLAY TABLE
    # ==========================================

    st.dataframe(
        timeframe_table,
        use_container_width=True,
        hide_index=True
    )
        # =========================
    # COT POSITIONING CHART
    # =========================

    st.divider()

    st.subheader("COT Positioning")

    # -------------------------
    # Chart controls
    # -------------------------

    control1, control2, control3 = st.columns(3)

    with control1:
        chart_group = st.selectbox(
            "Participant",
            [
                "Dealer",
                "Asset Manager",
                "Leveraged Funds",
                "Compare All"
            ]
        )

    with control2:
        position_type = st.selectbox(
    "Position Type",
    [
        "Net",
        "Long",
        "Short",
        "Long vs Short"
    ]
)

    with control3:
        chart_period = st.selectbox(
            "Period",
            [
                "6M",
                "1Y",
                "3Y"
            ],
            index=2
        )

    # -------------------------
    # Select time period
    # -------------------------

    latest_date = df[
        "report_date_as_yyyy_mm_dd"
    ].iloc[-1]

    if chart_period == "6M":
        start_date = latest_date - pd.DateOffset(months=6)

    elif chart_period == "1Y":
        start_date = latest_date - pd.DateOffset(years=1)

    else:
        start_date = latest_date - pd.DateOffset(years=3)

    chart_df = df[
        df["report_date_as_yyyy_mm_dd"] >= start_date
    ].copy()

    # -------------------------
    # Create chart
    # -------------------------

    fig = go.Figure()

    position_columns = {

        "Net": {
            "Dealer": "dealer_net",
            "Asset Manager": "asset_manager_net",
            "Leveraged Funds": "leveraged_funds_net"
        },

        "Long": {
            "Dealer": "dealer_positions_long_all",
            "Asset Manager": "asset_mgr_positions_long",
            "Leveraged Funds": "lev_money_positions_long"
        },

        "Short": {
            "Dealer": "dealer_positions_short_all",
            "Asset Manager": "asset_mgr_positions_short",
            "Leveraged Funds": "lev_money_positions_short"
        }
    }

    # ==========================================
    # LONG VS SHORT MODE
    # ==========================================

    if position_type == "Long vs Short":

        long_columns = position_columns["Long"]
        short_columns = position_columns["Short"]

        # --------------------------------------
        # Compare All
        # --------------------------------------

        if chart_group == "Compare All":

            for group_name in long_columns:

                long_column = long_columns[group_name]
                short_column = short_columns[group_name]

                fig.add_trace(
                    go.Scatter(
                        x=chart_df["report_date_as_yyyy_mm_dd"],
                        y=chart_df[long_column],
                        mode="lines",
                        name=f"{group_name} Long"
                    )
                )

                fig.add_trace(
                    go.Scatter(
                        x=chart_df["report_date_as_yyyy_mm_dd"],
                        y=chart_df[short_column],
                        mode="lines",
                        name=f"{group_name} Short",
                        line=dict(dash="dash")
                    )
                )

        # --------------------------------------
        # Individual participant
        # --------------------------------------

        else:

            long_column = long_columns[chart_group]
            short_column = short_columns[chart_group]

            # Long line

            fig.add_trace(
                go.Scatter(
                    x=chart_df["report_date_as_yyyy_mm_dd"],
                    y=chart_df[long_column],
                    mode="lines",
                    name="Long"
                )
            )

            # Short line

            fig.add_trace(
                go.Scatter(
                    x=chart_df["report_date_as_yyyy_mm_dd"],
                    y=chart_df[short_column],
                    mode="lines",
                    name="Short",
                    line=dict(dash="dash")
                )
            )

            # Current Long

            fig.add_trace(
                go.Scatter(
                    x=[
                        chart_df[
                            "report_date_as_yyyy_mm_dd"
                        ].iloc[-1]
                    ],
                    y=[
                        chart_df[long_column].iloc[-1]
                    ],
                    mode="markers",
                    marker=dict(size=10),
                    name="Current Long"
                )
            )

            # Current Short

            fig.add_trace(
                go.Scatter(
                    x=[
                        chart_df[
                            "report_date_as_yyyy_mm_dd"
                        ].iloc[-1]
                    ],
                    y=[
                        chart_df[short_column].iloc[-1]
                    ],
                    mode="markers",
                    marker=dict(size=10),
                    name="Current Short"
                )
            )

            # ----------------------------------
            # 3Y historical means
            # ----------------------------------

            start_3y = (
                latest_date
                - pd.DateOffset(years=3)
            )

            mean_df = df[
                df["report_date_as_yyyy_mm_dd"] >= start_3y
            ]

            long_mean = mean_df[long_column].mean()
            short_mean = mean_df[short_column].mean()

            fig.add_hline(
                y=long_mean,
                line_dash="dash",
                annotation_text=(
                    f"3Y Long Mean: {long_mean:,.0f}"
                )
            )

            fig.add_hline(
                y=short_mean,
                line_dash="dot",
                annotation_text=(
                    f"3Y Short Mean: {short_mean:,.0f}"
                )
            )

    # ==========================================
    # NORMAL NET / LONG / SHORT MODE
    # ==========================================

    else:

        chart_groups = position_columns[position_type]

        if chart_group == "Compare All":

            for group_name, column in chart_groups.items():

                fig.add_trace(
                    go.Scatter(
                        x=chart_df["report_date_as_yyyy_mm_dd"],
                        y=chart_df[column],
                        mode="lines",
                        name=group_name
                    )
                )

        else:

            column = chart_groups[chart_group]

            fig.add_trace(
                go.Scatter(
                    x=chart_df["report_date_as_yyyy_mm_dd"],
                    y=chart_df[column],
                    mode="lines",
                    name=chart_group
                )
            )

            # Current position marker

            fig.add_trace(
                go.Scatter(
                    x=[
                        chart_df[
                            "report_date_as_yyyy_mm_dd"
                        ].iloc[-1]
                    ],
                    y=[
                        chart_df[column].iloc[-1]
                    ],
                    mode="markers",
                    marker=dict(size=10),
                    name="Current"
                )
            )

            # 3Y historical mean

            start_3y = (
                latest_date
                - pd.DateOffset(years=3)
            )

            mean_df = df[
                df["report_date_as_yyyy_mm_dd"] >= start_3y
            ]

            historical_mean = mean_df[column].mean()

            fig.add_hline(
                y=historical_mean,
                line_dash="dash",
                annotation_text=(
                    f"3Y Mean: {historical_mean:,.0f}"
                )
            )

    # ==========================================
    # ZERO LINE
    # ==========================================

    fig.add_hline(
        y=0,
        line_width=1
    )

    # ==========================================
    # CHART DESIGN
    # ==========================================

    if position_type == "Long vs Short":
        y_axis_title = "Positions"
    else:
        y_axis_title = f"{position_type} Position"

    fig.update_layout(
        height=600,
        xaxis_title="Report Date",
        yaxis_title=y_axis_title,
        hovermode="x unified",
        margin=dict(
            l=20,
            r=20,
            t=30,
            b=20
        )
    )

    fig.update_yaxes(
        tickformat=","
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

except (RuntimeError, ValueError) as error:
    st.error(
        "Unable to load CFTC data right now."
    )

    st.info(
        "Please try again later or refresh the page."
    )

    st.caption(
        f"Technical details: {error}"
    )

except Exception as error:
    st.error(
        "An unexpected error occurred."
    )

    st.caption(
        f"Technical details: {error}"
    )

        