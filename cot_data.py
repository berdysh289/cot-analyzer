import requests
import pandas as pd
import streamlit as st


# ==========================================
# CFTC API
# ==========================================

URL = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"


# ==========================================
# MARKETS
# ==========================================

MARKETS = {
    "S&P 500": "S&P 500 Consolidated - CHICAGO MERCANTILE EXCHANGE",
    "NASDAQ-100": "NASDAQ-100 Consolidated - CHICAGO MERCANTILE EXCHANGE",
    "NIKKEI 225": "NIKKEI STOCK AVERAGE YEN DENOM - CHICAGO MERCANTILE EXCHANGE"
}


# ==========================================
# CFTC NUMERIC COLUMNS
# ==========================================

NUMERIC_COLUMNS = [
    "dealer_positions_long_all",
    "dealer_positions_short_all",
    "asset_mgr_positions_long",
    "asset_mgr_positions_short",
    "lev_money_positions_long",
    "lev_money_positions_short"
]


# ==========================================
# CALCULATE PERCENTILE
# ==========================================

def calculate_percentile(series):

    series = series.dropna()

    if series.empty:
        return 0.0

    current_value = series.iloc[-1]

    values_below = (series < current_value).sum()
    values_equal = (series == current_value).sum()

    percentile = (
        values_below + 0.5 * values_equal
    ) / len(series) * 100

    return percentile


# ==========================================
# CALCULATE Z-SCORE
# ==========================================

def calculate_zscore(series):

    series = series.dropna()

    if series.empty:
        return 0.0

    current_value = series.iloc[-1]

    mean = series.mean()
    std = series.std(ddof=0)

    if std == 0:
        return 0.0

    return (current_value - mean) / std


# ==========================================
# DOWNLOAD COT DATA
# ==========================================

@st.cache_data(ttl=3600)
def get_cot_data(market_name):

    if market_name not in MARKETS:
        raise ValueError(
            f"Unknown market: {market_name}"
        )

    cftc_market = MARKETS[market_name]

    params = {
        "$limit": 500,
        "$where": (
            f"market_and_exchange_names='{cftc_market}'"
        ),
        "$order": "report_date_as_yyyy_mm_dd DESC"
    }

    # --------------------------
    # Request CFTC data
    # --------------------------

    try:
        response = requests.get(
            URL,
            params=params,
            timeout=30
        )

        response.raise_for_status()

    except requests.exceptions.Timeout:
        raise RuntimeError(
            "CFTC API request timed out."
        )

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Unable to connect to the CFTC API."
        )

    except requests.exceptions.HTTPError as error:
        raise RuntimeError(
            f"CFTC API returned an HTTP error: {error}"
        )

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            f"CFTC API request failed: {error}"
        )

    # --------------------------
    # Convert response to JSON
    # --------------------------

    try:
        data = response.json()

    except ValueError:
        raise RuntimeError(
            "CFTC API returned invalid data."
        )

    df = pd.DataFrame(data)

    if df.empty:
        raise ValueError(
            f"No COT data received for {market_name}"
        )

    # --------------------------
    # Prepare dates
    # --------------------------

    df["report_date_as_yyyy_mm_dd"] = pd.to_datetime(
        df["report_date_as_yyyy_mm_dd"]
    )

    df = df.sort_values(
        "report_date_as_yyyy_mm_dd"
    ).reset_index(drop=True)

    # --------------------------
    # Convert positions to numbers
    # --------------------------

    for column in NUMERIC_COLUMNS:

        if column not in df.columns:
            raise ValueError(
                f"Missing CFTC column: {column}"
            )

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # --------------------------
    # Net Positions
    # --------------------------

    df["dealer_net"] = (
        df["dealer_positions_long_all"]
        - df["dealer_positions_short_all"]
    )

    df["asset_manager_net"] = (
        df["asset_mgr_positions_long"]
        - df["asset_mgr_positions_short"]
    )

    df["leveraged_funds_net"] = (
        df["lev_money_positions_long"]
        - df["lev_money_positions_short"]
    )

    return df


# ==========================================
# MARKET SUMMARY
# ==========================================
def classify_positioning(long_change, short_change):

    if long_change > 0 and short_change < 0:
        return "Long Building + Short Covering"

    elif long_change > 0 and short_change > 0:
        if long_change > short_change:
            return "Long Building"
        elif short_change > long_change:
            return "Short Building"
        else:
            return "Balanced Building"

    elif long_change < 0 and short_change < 0:
        if abs(short_change) > abs(long_change):
            return "Short Covering"
        elif abs(long_change) > abs(short_change):
            return "Long Liquidation"
        else:
            return "Balanced Reduction"

    elif long_change < 0 and short_change > 0:
        return "Long Liquidation + Short Building"

    elif long_change > 0 and short_change == 0:
        return "Long Building"

    elif long_change < 0 and short_change == 0:
        return "Long Liquidation"

    elif long_change == 0 and short_change > 0:
        return "Short Building"

    elif long_change == 0 and short_change < 0:
        return "Short Covering"

    else:
        return "No Major Change"


def calculate_change_strength(series):

    weekly_changes = series.diff().dropna()

    if weekly_changes.empty:
        return 0.0, "Normal"

    current_change = weekly_changes.iloc[-1]

    absolute_changes = weekly_changes.abs()
    current_absolute_change = abs(current_change)

    values_below = (
        absolute_changes < current_absolute_change
    ).sum()

    values_equal = (
        absolute_changes == current_absolute_change
    ).sum()

    strength_percentile = (
        (
            values_below
            + 0.5 * values_equal
        )
        / len(absolute_changes)
        * 100
    )

    if strength_percentile >= 95:
        strength = "Extreme"

    elif strength_percentile >= 80:
        strength = "Strong"

    elif strength_percentile >= 50:
        strength = "Moderate"

    else:
        strength = "Normal"

    return strength_percentile, strength

def classify_extreme(percentile, zscore):

    if percentile >= 95 and zscore >= 2:
        return "Extreme High"

    elif percentile >= 80:
        return "High"

    elif percentile <= 5 and zscore <= -2:
        return "Extreme Low"

    elif percentile <= 20:
        return "Low"

    else:
        return "Normal"
    
def get_market_summary(df):

    if len(df) < 2:
        raise ValueError(
            "Not enough COT reports to calculate changes."
        )

    latest = df.iloc[-1]

    latest_date = latest[
        "report_date_as_yyyy_mm_dd"
    ]

    start_3y = (
        latest_date
        - pd.DateOffset(years=3)
    )

    df_3y = df[
        df["report_date_as_yyyy_mm_dd"] >= start_3y
    ].copy()

    if len(df_3y) < 2:
        raise ValueError(
            "Not enough COT reports inside the 3Y window."
        )

    groups = {
        "Dealer": {
            "net": "dealer_net",
            "long": "dealer_positions_long_all",
            "short": "dealer_positions_short_all"
        },

        "Asset Manager": {
            "net": "asset_manager_net",
            "long": "asset_mgr_positions_long",
            "short": "asset_mgr_positions_short"
        },

        "Leveraged Funds": {
            "net": "leveraged_funds_net",
            "long": "lev_money_positions_long",
            "short": "lev_money_positions_short"
        }
    }

    summary = {}

    for group_name, columns in groups.items():

        net_column = columns["net"]
        long_column = columns["long"]
        short_column = columns["short"]

        # ==================================
        # CURRENT POSITIONS
        # ==================================

        current_net = df_3y[net_column].iloc[-1]
        current_long = df_3y[long_column].iloc[-1]
        current_short = df_3y[short_column].iloc[-1]

        previous_net = df_3y[net_column].iloc[-2]
        previous_long = df_3y[long_column].iloc[-2]
        previous_short = df_3y[short_column].iloc[-2]

        # ==================================
        # WEEKLY CHANGES
        # ==================================

        weekly_change = (
            current_net - previous_net
        )

        long_weekly_change = (
            current_long - previous_long
        )

        short_weekly_change = (
            current_short - previous_short
        )

        # ==================================
        # POSITIONING SIGNAL
        # ==================================

        positioning_signal = classify_positioning(
            long_weekly_change,
            short_weekly_change
        )

        # ==================================
        # DIRECTION
        # ==================================

        if weekly_change > 0:
            direction = "Bullish Shift"

        elif weekly_change < 0:
            direction = "Bearish Shift"

        else:
            direction = "Neutral"

        # ==================================
        # LONG / SHORT RATIO
        # ==================================

        if current_short == 0:
            long_short_ratio = None
        else:
            long_short_ratio = (
                current_long / current_short
            )

        # ==================================
        # NET HISTORICAL ANALYSIS
        # ==================================

        percentile = calculate_percentile(
            df_3y[net_column]
        )

        zscore = calculate_zscore(
            df_3y[net_column]
        )

        # ==================================
        # WEEKLY CHANGE STRENGTH
        # ==================================

        strength_percentile, strength = calculate_change_strength(
            df_3y[net_column]
        )

        # ==================================
        # LONG HISTORICAL ANALYSIS
        # ==================================

        long_percentile = calculate_percentile(
            df_3y[long_column]
        )

        long_zscore = calculate_zscore(
            df_3y[long_column]
        )

        # ==================================
        # SHORT HISTORICAL ANALYSIS
        # ==================================

        short_percentile = calculate_percentile(
            df_3y[short_column]
        )

        short_zscore = calculate_zscore(
            df_3y[short_column]
        )
        # ==================================
        # POSITION EXTREME STATES
        # ==================================

        net_state = classify_extreme(
            percentile,
            zscore
        )

        long_state = classify_extreme(
            long_percentile,
            long_zscore
        )

        short_state = classify_extreme(
            short_percentile,
            short_zscore
        )

        # ==================================
        # SUMMARY
        # ==================================

        summary[group_name] = {

            "long": current_long,
            "long_weekly_change": long_weekly_change,
            "long_percentile": long_percentile,
            "long_zscore": long_zscore,
            "long_state": long_state,

            "short": current_short,
            "short_weekly_change": short_weekly_change,
            "short_percentile": short_percentile,
            "short_zscore": short_zscore,
            "short_state": short_state,

            "long_short_ratio": long_short_ratio,

            "net": current_net,
            "weekly_change": weekly_change,
            "percentile": percentile,
            "zscore": zscore,
            "net_state": net_state,

            "strength_percentile": strength_percentile,
            "strength": strength,

            "direction": direction,
            "positioning_signal": positioning_signal
        }

    return summary

def get_strength_weight(strength):

    weights = {
        "Normal": 1,
        "Moderate": 2,
        "Strong": 3,
        "Extreme": 4
    }

    return weights.get(strength, 1)

def get_positioning_quality(direction, positioning):

    # ==================================
    # BULLISH SHIFT
    # ==================================

    if direction == "Bullish Shift":

        if positioning == "Long Building + Short Covering":
            return "Strong Bullish Flow", 2

        elif positioning == "Long Building":
            return "Bullish New Positioning", 2

        elif positioning == "Short Covering":
            return "Bullish Short Covering", 1

        else:
            return "Bullish Mixed Flow", 1

    # ==================================
    # BEARISH SHIFT
    # ==================================

    elif direction == "Bearish Shift":

        if positioning == "Long Liquidation + Short Building":
            return "Strong Bearish Flow", -2

        elif positioning == "Short Building":
            return "Bearish New Positioning", -2

        elif positioning == "Long Liquidation":
            return "Bearish Long Liquidation", -1

        else:
            return "Bearish Mixed Flow", -1

    # ==================================
    # NEUTRAL
    # ==================================

    else:
        return "Neutral Flow", 0

def classify_flow_type(positioning):

    active_flows = [
        "Long Building",
        "Short Building",
        "Long Liquidation + Short Building",
        "Long Building + Short Covering"
    ]

    passive_flows = [
        "Long Liquidation",
        "Short Covering"
    ]

    if positioning in active_flows:
        return "Active"

    elif positioning in passive_flows:
        return "Passive"

    else:
        return "Mixed"
        
def calculate_regime_confirmation_score(
    asset_mtf_score,
    leveraged_mtf_score,
    asset_strength_percentile,
    leveraged_strength_percentile
):
    # ==================================
    # 1. MULTI-TIMEFRAME CONFIRMATION
    # ==================================

    asset_mtf_percent = (
        asset_mtf_score / 3 * 100
    )

    leveraged_mtf_percent = (
        leveraged_mtf_score / 3 * 100
    )

    mtf_score = (
        asset_mtf_percent
        + leveraged_mtf_percent
    ) / 2

    # ==================================
    # 2. WEEKLY FLOW STRENGTH
    # ==================================

    strength_score = (
        asset_strength_percentile
        + leveraged_strength_percentile
    ) / 2

    # ==================================
    # FINAL CONFIRMATION SCORE
    # ==================================

    confirmation_score = (
        mtf_score * 0.70
        + strength_score * 0.30
    )

    # ==================================
    # CONFIDENCE LABEL
    # ==================================

    if confirmation_score >= 80:
        confirmation_label = "Very High"

    elif confirmation_score >= 65:
        confirmation_label = "High"

    elif confirmation_score >= 50:
        confirmation_label = "Moderate"

    elif confirmation_score >= 35:
        confirmation_label = "Low"

    else:
        confirmation_label = "Very Low"

    return confirmation_score, confirmation_label
    

def calculate_regime_confidence(
    asset_strength_percentile,
    leveraged_strength_percentile
):

    average_strength = (
        asset_strength_percentile
        + leveraged_strength_percentile
    ) / 2

    if average_strength >= 90:
        confidence = "Very High"

    elif average_strength >= 75:
        confidence = "High"

    elif average_strength >= 50:
        confidence = "Moderate"

    else:
        confidence = "Low"

    return average_strength, confidence

def classify_timeframe_direction(change):

    if change > 0:
        return "Bullish"

    elif change < 0:
        return "Bearish"

    else:
        return "Neutral"

def combine_timeframe_directions(first_direction, second_direction):

    if (
        first_direction == "Bullish"
        and second_direction == "Bullish"
    ):
        return "Bullish"

    elif (
        first_direction == "Bearish"
        and second_direction == "Bearish"
    ):
        return "Bearish"

    else:
        return "Mixed"

def classify_positioning_trend(
    current_1w,
    short_term,
    medium_term
):

    # ==================================
    # BULLISH CONTINUATION
    # ==================================

    if (
        current_1w == "Bullish"
        and short_term == "Bullish"
        and medium_term == "Bullish"
    ):
        return "Bullish Continuation"


    # ==================================
    # BEARISH CONTINUATION
    # ==================================

    elif (
        current_1w == "Bearish"
        and short_term == "Bearish"
        and medium_term == "Bearish"
    ):
        return "Bearish Continuation"


    # ==================================
    # BULLISH TRANSITION
    # ==================================

    elif (
        current_1w == "Bullish"
        and short_term == "Bullish"
        and medium_term != "Bullish"
    ):
        return "Bullish Transition"


    # ==================================
    # BEARISH TRANSITION
    # ==================================

    elif (
        current_1w == "Bearish"
        and short_term == "Bearish"
        and medium_term != "Bearish"
    ):
        return "Bearish Transition"


    # ==================================
    # BULLISH COUNTER-TREND SHIFT
    # ==================================

    elif (
        current_1w == "Bullish"
        and short_term == "Mixed"
        and medium_term == "Bearish"
    ):
        return "Bullish Counter-Trend Shift"


    # ==================================
    # BEARISH COUNTER-TREND SHIFT
    # ==================================

    elif (
        current_1w == "Bearish"
        and short_term == "Mixed"
        and medium_term == "Bullish"
    ):
        return "Bearish Counter-Trend Shift"


    # ==================================
    # MIXED
    # ==================================

    else:
        return "Mixed / Unconfirmed"        

def get_multitimeframe_context(changes):
    

    # ==================================
    # HELPER
    # ==================================

    def get_direction(group, period):

        value = changes[group]["Net"][period]

        if value is None:
            return "Neutral"

        return classify_timeframe_direction(value)


    # ==================================
    # ASSET MANAGER
    # ==================================

    asset_1w = get_direction(
        "Asset Manager", "1W"
    )

    asset_1m = get_direction(
        "Asset Manager", "1M"
    )

    asset_3m = get_direction(
        "Asset Manager", "3M"
    )

    asset_6m = get_direction(
        "Asset Manager", "6M"
    )

    asset_1y = get_direction(
        "Asset Manager", "1Y"
    )

    asset_3y = get_direction(
        "Asset Manager", "3Y"
    )


    # ==================================
    # LEVERAGED FUNDS
    # ==================================

    leveraged_1w = get_direction(
        "Leveraged Funds", "1W"
    )

    leveraged_1m = get_direction(
        "Leveraged Funds", "1M"
    )

    leveraged_3m = get_direction(
        "Leveraged Funds", "3M"
    )

    leveraged_6m = get_direction(
        "Leveraged Funds", "6M"
    )

    leveraged_1y = get_direction(
        "Leveraged Funds", "1Y"
    )

    leveraged_3y = get_direction(
        "Leveraged Funds", "3Y"
    )


    # ==================================
    # ASSET MANAGER TIMEFRAME REGIMES
    # ==================================

    asset_short_term = combine_timeframe_directions(
        asset_1w,
        asset_1m
    )

    asset_medium_term = combine_timeframe_directions(
        asset_3m,
        asset_6m
    )

    asset_long_term = combine_timeframe_directions(
        asset_1y,
        asset_3y
    )


    # ==================================
    # LEVERAGED FUNDS TIMEFRAME REGIMES
    # ==================================

    leveraged_short_term = combine_timeframe_directions(
        leveraged_1w,
        leveraged_1m
    )

    leveraged_medium_term = combine_timeframe_directions(
        leveraged_3m,
        leveraged_6m
    )

    leveraged_long_term = combine_timeframe_directions(
        leveraged_1y,
        leveraged_3y
    )

    # ==================================
    # POSITIONING TREND STATE
    # ==================================

    asset_trend_state = classify_positioning_trend(
        asset_1w,
        asset_short_term,
        asset_medium_term
    )

    leveraged_trend_state = classify_positioning_trend(
        leveraged_1w,
        leveraged_short_term,
        leveraged_medium_term
    )


    # ==================================
    # RETURN
    # ==================================

    return {
        # Asset Manager
        "asset_1w": asset_1w,
        "asset_1m": asset_1m,
        "asset_3m": asset_3m,
        "asset_6m": asset_6m,
        "asset_1y": asset_1y,
        "asset_3y": asset_3y,

        "asset_short_term": asset_short_term,
        "asset_medium_term": asset_medium_term,
        "asset_long_term": asset_long_term,
        "asset_trend_state": asset_trend_state,

        # Leveraged Funds
        "leveraged_1w": leveraged_1w,
        "leveraged_1m": leveraged_1m,
        "leveraged_3m": leveraged_3m,
        "leveraged_6m": leveraged_6m,
        "leveraged_1y": leveraged_1y,
        "leveraged_3y": leveraged_3y,

        "leveraged_short_term": leveraged_short_term,
        "leveraged_medium_term": leveraged_medium_term,
        "leveraged_long_term": leveraged_long_term,
        "leveraged_trend_state": leveraged_trend_state
    }

def generate_cot_summary(
    regime,
    multitimeframe_context
):

    # ==================================
    # ASSET MANAGER
    # ==================================

    asset_direction = regime["asset_direction"]
    asset_flow_type = regime["asset_flow_type"]
    asset_positioning = regime["asset_positioning"]
    asset_strength = regime["asset_strength"]
    asset_historical = regime["asset_historical_context"]

    asset_trend = multitimeframe_context[
        "asset_trend_state"
    ]


    # ==================================
    # LEVERAGED FUNDS
    # ==================================

    leveraged_direction = regime["leveraged_direction"]
    leveraged_flow_type = regime["leveraged_flow_type"]
    leveraged_positioning = regime["leveraged_positioning"]
    leveraged_strength = regime["leveraged_strength"]
    leveraged_historical = regime[
        "leveraged_historical_context"
    ]

    leveraged_trend = multitimeframe_context[
        "leveraged_trend_state"
    ]


    # ==================================
    # DEALER
    # ==================================

    dealer_direction = regime["dealer_direction"]
    dealer_historical = regime[
        "dealer_historical_context"
    ]


    # ==================================
    # BUILD SUMMARY
    # ==================================

    asset_text = (
        f"Asset Managers show a {asset_direction.lower()} "
        f"with {asset_flow_type.lower()} positioning. "
        f"The current behavior is {asset_positioning.lower()}, "
        f"with {asset_strength.lower()} weekly strength. "
        f"The broader positioning trend is "
        f"{asset_trend.lower()}."
    )

    leveraged_text = (
        f"Leveraged Funds show a "
        f"{leveraged_direction.lower()} "
        f"with {leveraged_flow_type.lower()} positioning. "
        f"The current behavior is "
        f"{leveraged_positioning.lower()}, "
        f"with {leveraged_strength.lower()} weekly strength. "
        f"The broader positioning trend is "
        f"{leveraged_trend.lower()}."
    )


    # ==================================
    # HISTORICAL CONTEXT
    # ==================================

    if (
        asset_historical == "Extreme"
        or leveraged_historical == "Extreme"
    ):
        historical_text = (
            "At least one major participant group is "
            "positioned at a historically extreme level."
        )

    elif (
        asset_historical == "Elevated"
        or leveraged_historical == "Elevated"
    ):
        historical_text = (
            "Positioning is historically elevated, "
            "but not extreme."
        )

    else:
        historical_text = (
            "Asset Manager and Leveraged Fund positioning "
            "is currently within normal historical ranges."
        )


    # ==================================
    # DEALER CONTEXT
    # ==================================

    dealer_text = (
        f"Dealer positioning is currently showing a "
        f"{dealer_direction.lower()} and remains in a "
        f"{dealer_historical.lower()} historical range."
    )


    return {
        "asset_summary": asset_text,
        "leveraged_summary": leveraged_text,
        "historical_summary": historical_text,
        "dealer_summary": dealer_text
    }

def get_historical_context(group):

    net_state = group["net_state"]
    long_state = group["long_state"]
    short_state = group["short_state"]

    # ==================================
    # EXTREME
    # ==================================

    if (
        "Extreme" in net_state
        or "Extreme" in long_state
        or "Extreme" in short_state
    ):
        context = "Extreme"

    # ==================================
    # ELEVATED
    # ==================================

    elif (
        net_state in ["High", "Low"]
        or long_state in ["High", "Low"]
        or short_state in ["High", "Low"]
    ):
        context = "Elevated"

    # ==================================
    # NORMAL
    # ==================================

    else:
        context = "Normal"

    return context

def calculate_mtf_confirmation(
    direction,
    short_term,
    medium_term,
    long_term
):
    if direction == "Bullish Shift":
        target = "Bullish"

    elif direction == "Bearish Shift":
        target = "Bearish"

    else:
        return 0, "Unconfirmed"

    contexts = [
        short_term,
        medium_term,
        long_term
    ]

    confirmations = contexts.count(target)

    if confirmations == 3:
        status = "Full Confirmation"

    elif confirmations == 2:
        status = "Confirmed"

    elif confirmations == 1:
        status = "Partial Confirmation"

    else:
        status = "Counter-Trend"

    return confirmations, status


def get_cot_regime(summary, multitimeframe_context):

    asset = summary["Asset Manager"]
    leveraged = summary["Leveraged Funds"]
    dealer = summary["Dealer"]

    # ==================================
    # MULTI-TIMEFRAME CONTEXT
    # ==================================

    asset_short_term = multitimeframe_context["asset_short_term"]
    asset_medium_term = multitimeframe_context["asset_medium_term"]
    asset_long_term = multitimeframe_context["asset_long_term"]

    leveraged_short_term = multitimeframe_context["leveraged_short_term"]
    leveraged_medium_term = multitimeframe_context["leveraged_medium_term"]
    leveraged_long_term = multitimeframe_context["leveraged_long_term"]

    # ==================================
    # MTF CONFIRMATION
    # ==================================

    asset_mtf_score, asset_mtf_status = calculate_mtf_confirmation(
        asset["direction"],
        asset_short_term,
        asset_medium_term,
        asset_long_term
    )

    leveraged_mtf_score, leveraged_mtf_status = calculate_mtf_confirmation(
        leveraged["direction"],
        leveraged_short_term,
        leveraged_medium_term,
        leveraged_long_term
    )

    # ==================================
    # HISTORICAL POSITIONING CONTEXT
    # ==================================

    asset_historical_context = get_historical_context(asset)
    leveraged_historical_context = get_historical_context(leveraged)
    dealer_historical_context = get_historical_context(dealer)

    asset_direction = asset["direction"]
    leveraged_direction = leveraged["direction"]
    dealer_direction = dealer["direction"]

    # ==================================
    # POSITIONING DETAILS
    # ==================================

    asset_strength = asset["strength"]
    leveraged_strength = leveraged["strength"]
    dealer_strength = dealer["strength"]

    asset_strength_percentile = asset["strength_percentile"]
    leveraged_strength_percentile = leveraged["strength_percentile"]
    dealer_strength_percentile = dealer["strength_percentile"]

    asset_positioning = asset["positioning_signal"]
    leveraged_positioning = leveraged["positioning_signal"]
    dealer_positioning = dealer["positioning_signal"]

    # ==================================
    # DIRECTIONAL SCORES
    # ==================================

    def direction_score(direction, strength):

        weight = get_strength_weight(strength)

        if direction == "Bullish Shift":
            return weight

        elif direction == "Bearish Shift":
            return -weight

        else:
            return 0

    asset_score = direction_score(
        asset_direction,
        asset_strength
    )

    leveraged_score = direction_score(
        leveraged_direction,
        leveraged_strength
    )

    dealer_score = direction_score(
        dealer_direction,
        dealer_strength
    )

    # ==================================
    # POSITIONING QUALITY
    # ==================================

    asset_flow, asset_flow_score = get_positioning_quality(
        asset_direction,
        asset_positioning
    )

    leveraged_flow, leveraged_flow_score = get_positioning_quality(
        leveraged_direction,
        leveraged_positioning
    )

    dealer_flow, dealer_flow_score = get_positioning_quality(
        dealer_direction,
        dealer_positioning
    )

    # ==================================
    # FLOW TYPE
    # ==================================

    asset_flow_type = classify_flow_type(
        asset_positioning
    )

    leveraged_flow_type = classify_flow_type(
        leveraged_positioning
    )

    dealer_flow_type = classify_flow_type(
        dealer_positioning
    )

    # ==================================
    # REGIME CONFIDENCE
    # ==================================

    regime_strength, regime_confidence = calculate_regime_confidence(
        asset_strength_percentile,
        leveraged_strength_percentile
    )

    # ==================================
    # REGIME CONFIRMATION SCORE
    # ==================================

    confirmation_score, confirmation_label = (
    calculate_regime_confirmation_score(
        asset_mtf_score,
        leveraged_mtf_score,
        asset_strength_percentile,
        leveraged_strength_percentile
        )
    )

    # ==================================
    # REGIME ENGINE V1.0
    # ==================================

    if (
        asset_direction == "Bullish Shift"
        and leveraged_direction == "Bullish Shift"
    ):

        if (
            asset_mtf_score >= 2
            and leveraged_mtf_score >= 2
        ):
            regime = "Broad Bullish Alignment"

        elif (
            asset_mtf_score == 0
            and leveraged_mtf_score == 0
        ):
            regime = "Bullish Counter-Trend Alignment"

        else:
            regime = "Partial Bullish Alignment"


    elif (
        asset_direction == "Bearish Shift"
        and leveraged_direction == "Bearish Shift"
    ):

        if (
            asset_mtf_score >= 2
            and leveraged_mtf_score >= 2
        ):
            regime = "Broad Bearish Alignment"

        elif (
            asset_mtf_score == 0
            and leveraged_mtf_score == 0
        ):
            regime = "Bearish Counter-Trend Alignment"

        else:
            regime = "Partial Bearish Alignment"


    elif (
        asset_direction == "Bullish Shift"
        and leveraged_direction == "Bearish Shift"
    ):

        if (
            asset_mtf_score >= 2
            and leveraged_mtf_score >= 2
        ):
            regime = "Confirmed Divergence"

        elif (
            asset_mtf_score >= 2
            and leveraged_mtf_score <= 1
        ):
            regime = "Asset-Led Bullish Divergence"

        elif (
            leveraged_mtf_score >= 2
            and asset_mtf_score <= 1
        ):
            regime = "Leveraged-Led Bearish Divergence"

        else:
            regime = "Unconfirmed Divergence"


    elif (
        asset_direction == "Bearish Shift"
        and leveraged_direction == "Bullish Shift"
    ):

        if (
            asset_mtf_score >= 2
            and leveraged_mtf_score >= 2
        ):
            regime = "Confirmed Divergence"

        elif (
            asset_mtf_score >= 2
            and leveraged_mtf_score <= 1
        ):
            regime = "Asset-Led Bearish Divergence"

        elif (
            leveraged_mtf_score >= 2
            and asset_mtf_score <= 1
        ):
            regime = "Leveraged-Led Bullish Divergence"

        else:
            regime = "Unconfirmed Divergence"


    else:
        regime = "Mixed / Transitional"

        # ==================================
        # DIVERGENCE TYPE
        # ==================================

    if (
            asset_direction == "Bullish Shift"
            and leveraged_direction == "Bearish Shift"
        ):
            divergence = (
                "Asset Managers Bullish / "
                "Leveraged Funds Bearish"
            )

    elif (
            asset_direction == "Bearish Shift"
            and leveraged_direction == "Bullish Shift"
        ):
            divergence = (
                "Asset Managers Bearish / "
                "Leveraged Funds Bullish"
            )

    else:
            divergence = "None"

    # ==================================
    # RESULT
    # ==================================

    return {
        "regime": regime,
        "divergence": divergence,
        "regime_strength": regime_strength,
        "regime_confidence": regime_confidence,
        "confirmation_score": confirmation_score,
        "confirmation_label": confirmation_label,

        "asset_score": asset_score,
        "leveraged_score": leveraged_score,
        "dealer_score": dealer_score,

        "asset_direction": asset_direction,
        "asset_strength": asset_strength,
        "asset_strength_percentile": asset_strength_percentile,
        "asset_positioning": asset_positioning,
        "asset_flow": asset_flow,
        "asset_flow_score": asset_flow_score,
        "asset_flow_type": asset_flow_type,
        "asset_historical_context": asset_historical_context,
        "asset_mtf_score": asset_mtf_score,
        "asset_mtf_status": asset_mtf_status,

        "leveraged_direction": leveraged_direction,
        "leveraged_strength": leveraged_strength,
        "leveraged_strength_percentile": leveraged_strength_percentile,
        "leveraged_positioning": leveraged_positioning,
        "leveraged_flow": leveraged_flow,
        "leveraged_flow_score": leveraged_flow_score,
        "leveraged_flow_type": leveraged_flow_type,
        "leveraged_historical_context": leveraged_historical_context,
        "leveraged_mtf_score": leveraged_mtf_score,
        "leveraged_mtf_status": leveraged_mtf_status,

        "dealer_direction": dealer_direction,
        "dealer_strength": dealer_strength,
        "dealer_strength_percentile": dealer_strength_percentile,
        "dealer_positioning": dealer_positioning,
        "dealer_flow": dealer_flow,
        "dealer_flow_score": dealer_flow_score,
        "dealer_flow_type": dealer_flow_type,
        "dealer_historical_context": dealer_historical_context,
    }

# ==========================================
# MULTI-TIMEFRAME POSITION CHANGES
# ==========================================

def get_multitimeframe_changes(df):

    latest_date = df[
        "report_date_as_yyyy_mm_dd"
    ].iloc[-1]

    # ==========================================
    # TIMEFRAMES
    # ==========================================

    periods = {
        "1W": pd.DateOffset(weeks=1),
        "1M": pd.DateOffset(months=1),
        "3M": pd.DateOffset(months=3),
        "6M": pd.DateOffset(months=6),
        "1Y": pd.DateOffset(years=1),
        "3Y": pd.DateOffset(years=3)
    }

    # ==========================================
    # PARTICIPANTS + POSITION COLUMNS
    # ==========================================

    groups = {

        "Dealer": {
            "Long": "dealer_positions_long_all",
            "Short": "dealer_positions_short_all",
            "Net": "dealer_net"
        },

        "Asset Manager": {
            "Long": "asset_mgr_positions_long",
            "Short": "asset_mgr_positions_short",
            "Net": "asset_manager_net"
        },

        "Leveraged Funds": {
            "Long": "lev_money_positions_long",
            "Short": "lev_money_positions_short",
            "Net": "leveraged_funds_net"
        }
    }

    results = {}

    # ==========================================
    # CALCULATE CHANGES
    # ==========================================

    for group_name, position_columns in groups.items():

        results[group_name] = {}

        for position_type, column in position_columns.items():

            results[group_name][position_type] = {}

            current_value = df[column].iloc[-1]

            for period_name, offset in periods.items():

                target_date = latest_date - offset

                historical_data = df[
                    df["report_date_as_yyyy_mm_dd"] <= target_date
                ]

                if historical_data.empty:

                    results[group_name][position_type][
                        period_name
                    ] = None

                    continue

                historical_value = (
                    historical_data[column].iloc[-1]
                )

                change = (
                    current_value
                    - historical_value
                )

                results[group_name][position_type][
                    period_name
                ] = change

    return results