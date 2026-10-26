import requests
import pandas as pd
from datetime import timedelta

URL = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"

# ============================================================
# 1. AVAILABLE MARKETS
# ============================================================

MARKETS = {
    "1": {
        "name": "S&P 500",
        "cftc_name": "S&P 500 Consolidated - CHICAGO MERCANTILE EXCHANGE"
    },

    "2": {
        "name": "NASDAQ-100",
        "cftc_name": "NASDAQ-100 Consolidated - CHICAGO MERCANTILE EXCHANGE"
    },

    "3": {
        "name": "NIKKEI 225",
        "cftc_name": "NIKKEI STOCK AVERAGE YEN DENOM - CHICAGO MERCANTILE EXCHANGE"
    }
}

# ============================================================
# 2. CHOOSE MARKET
# ============================================================

print("\n" + "=" * 45)
print("COT ANALYZER")
print("=" * 45)

print("\nChoose market:\n")

print("1 - S&P 500")
print("2 - NASDAQ-100")
print("3 - NIKKEI 225")

choice = input("\nEnter market: ")

if choice not in MARKETS:
    print("\nERROR: Invalid market.")
    raise SystemExit

market_info = MARKETS[choice]

MARKET_NAME = market_info["name"]
MARKET = market_info["cftc_name"]

print(f"\nSelected market: {MARKET_NAME}")

# ============================================================
# 3. FIND LATEST AVAILABLE COT REPORT
# ============================================================

print("\nFinding latest COT report...")

latest_params = {
    "$limit": 1,
    "$where": f"market_and_exchange_names='{MARKET}'",
    "$order": "report_date_as_yyyy_mm_dd DESC"
}

latest_response = requests.get(
    URL,
    params=latest_params,
    timeout=30
)

latest_response.raise_for_status()

latest_data = latest_response.json()

if not latest_data:
    print("ERROR: No COT data found.")
    raise SystemExit

latest_report_date = pd.to_datetime(
    latest_data[0]["report_date_as_yyyy_mm_dd"]
)

# ============================================================
# 4. CALCULATE 3 YEAR WINDOW
# ============================================================

three_years_ago = latest_report_date - pd.DateOffset(years=3)

# Download a little extra history.
# This allows us to find the COT report
# immediately before the 3Y target date.
download_start = (
    three_years_ago - pd.DateOffset(months=2)
)

start_date = download_start.strftime(
    "%Y-%m-%dT00:00:00"
)

end_date = latest_report_date.strftime(
    "%Y-%m-%dT23:59:59"
)

print(
    f"Latest report: "
    f"{latest_report_date.strftime('%Y-%m-%d')}"
)

print(
    f"3Y window: "
    f"{three_years_ago.strftime('%Y-%m-%d')} "
    f"to "
    f"{latest_report_date.strftime('%Y-%m-%d')}"
)

# ============================================================
# 5. DOWNLOAD 3 YEARS OF DATA
# ============================================================

print("\nDownloading COT data...")

params = {
    "$limit": 500,

    "$where": (
        f"market_and_exchange_names='{MARKET}' "
        f"AND report_date_as_yyyy_mm_dd >= '{start_date}' "
        f"AND report_date_as_yyyy_mm_dd <= '{end_date}'"
    ),

    "$order": "report_date_as_yyyy_mm_dd ASC"
}

response = requests.get(
    URL,
    params=params,
    timeout=30
)

response.raise_for_status()

data = response.json()

df = pd.DataFrame(data)

if df.empty:
    print("ERROR: No COT data received.")
    raise SystemExit

# ============================================================
# 6. PREPARE DATA
# ============================================================

df["report_date_as_yyyy_mm_dd"] = pd.to_datetime(
    df["report_date_as_yyyy_mm_dd"]
)

columns = [
    "dealer_positions_long_all",
    "dealer_positions_short_all",

    "asset_mgr_positions_long",
    "asset_mgr_positions_short",

    "lev_money_positions_long",
    "lev_money_positions_short",

    "change_in_dealer_long_all",
    "change_in_dealer_short_all",

    "change_in_asset_mgr_long",
    "change_in_asset_mgr_short",

    "change_in_lev_money_long",
    "change_in_lev_money_short"
]

for column in columns:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )

    

# ============================================================
# 7. CALCULATE NET POSITIONS
# ============================================================

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
# ============================================================
# EXACT 3 YEAR DATASET
# ============================================================

df_3y = df[
    df["report_date_as_yyyy_mm_dd"] >= three_years_ago
].copy()

# ============================================================
# 8. PERCENTILE
# ============================================================

def calculate_percentile(series):

    series = series.dropna()

    current_value = series.iloc[-1]

    values_below = (series < current_value).sum()
    values_equal = (series == current_value).sum()

    percentile = (
        values_below + 0.5 * values_equal
    ) / len(series) * 100

    return percentile

# ============================================================
# 9. Z-SCORE
# ============================================================

def calculate_zscore(series):

    series = series.dropna()

    current_value = series.iloc[-1]

    average = series.mean()

    standard_deviation = series.std(ddof=0)

    if standard_deviation == 0:
        return 0.0

    return (
        current_value - average
    ) / standard_deviation

# ============================================================
# 10. CURRENT REPORT
# ============================================================

current = df.iloc[-1]

# ============================================================
# 11. GROUP SETTINGS
# ============================================================

groups = {

    "Dealer": {
        "long": "dealer_positions_long_all",
        "short": "dealer_positions_short_all",
        "net": "dealer_net",

        "delta_long": "change_in_dealer_long_all",
        "delta_short": "change_in_dealer_short_all"
    },

    "Asset Manager": {
        "long": "asset_mgr_positions_long",
        "short": "asset_mgr_positions_short",
        "net": "asset_manager_net",

        "delta_long": "change_in_asset_mgr_long",
        "delta_short": "change_in_asset_mgr_short"
    },

    "Leveraged Funds": {
        "long": "lev_money_positions_long",
        "short": "lev_money_positions_short",
        "net": "leveraged_funds_net",

        "delta_long": "change_in_lev_money_long",
        "delta_short": "change_in_lev_money_short"
    }
}

# ============================================================
# 12. CALCULATE RESULTS
# ============================================================

results = []

for group_name, cols in groups.items():

    current_long = current[cols["long"]]
    current_short = current[cols["short"]]
    current_net = current[cols["net"]]

    delta_long = current[cols["delta_long"]]
    delta_short = current[cols["delta_short"]]

    delta_net = delta_long - delta_short

    percentile = calculate_percentile(
        df_3y[cols["net"]]
    )

    zscore = calculate_zscore(
        df_3y[cols["net"]]
    )

    results.append({

        "Group": group_name,

        "Long": current_long,
        "Delta Long": delta_long,

        "Short": current_short,
        "Delta Short": delta_short,

        "Net": current_net,
        "Delta Net": delta_net,

        "Percentile": percentile,
        "Z-Score": zscore
    })
# ============================================================
# MULTI-TIMEFRAME NET POSITION CHANGE
# ============================================================

def get_net_at_or_before(target_date, column):

    historical_data = df[
        df["report_date_as_yyyy_mm_dd"] <= target_date
    ]

    if historical_data.empty:
        return None

    historical_report = historical_data.iloc[-1]

    return historical_report[column]


# Target dates
target_dates = {
    "1W": latest_report_date - pd.DateOffset(weeks=1),
    "1M": latest_report_date - pd.DateOffset(months=1),
    "3M": latest_report_date - pd.DateOffset(months=3),
    "6M": latest_report_date - pd.DateOffset(months=6),
    "1Y": latest_report_date - pd.DateOffset(years=1),
    "3Y": latest_report_date - pd.DateOffset(years=3)
}


# Calculate changes for every group
timeframe_changes = {}

for group_name, cols in groups.items():

    current_net = current[cols["net"]]

    timeframe_changes[group_name] = {}

    for timeframe, target_date in target_dates.items():

        historical_net = get_net_at_or_before(
            target_date,
            cols["net"]
        )

        if historical_net is None:
            change = None
        else:
            change = current_net - historical_net

        timeframe_changes[group_name][timeframe] = change

# ============================================================
# 13. DISPLAY RESULTS
# ============================================================

report_date = current[
    "report_date_as_yyyy_mm_dd"
].strftime("%Y-%m-%d")

print("\n" + "=" * 135)

print(f"{MARKET_NAME} — COT ANALYZER")

print("=" * 135)

print(f"Report date: {report_date}")

print(
    f"3Y window: "
    f"{three_years_ago.strftime('%Y-%m-%d')} "
    f"to {report_date}"
)

print(f"3Y reports analyzed: {len(df_3y)}")
print(f"Total reports loaded: {len(df)}")

print()

print(
    f"{'Group':<18}"
    f"{'Long':>13}"
    f"{'Δ Long':>13}"
    f"{'Short':>13}"
    f"{'Δ Short':>13}"
    f"{'Net':>14}"
    f"{'Δ Net':>13}"
    f"{'3Y %ile':>11}"
    f"{'Z-Score':>11}"
)

print("-" * 135)

for result in results:

    print(
        f"{result['Group']:<18}"

        f"{result['Long']:>13,.0f}"
        f"{result['Delta Long']:>+13,.0f}"

        f"{result['Short']:>13,.0f}"
        f"{result['Delta Short']:>+13,.0f}"

        f"{result['Net']:>+14,.0f}"
        f"{result['Delta Net']:>+13,.0f}"

        f"{result['Percentile']:>10.1f}%"

        f"{result['Z-Score']:>+11.2f}"
    )

print("=" * 135)
# ============================================================
# DISPLAY MULTI-TIMEFRAME CHANGES
# ============================================================

print("\nMULTI-TIMEFRAME NET POSITION CHANGE")

print("=" * 100)

print(
    f"{'Group':<20}"
    f"{'1W':>13}"
    f"{'1M':>13}"
    f"{'3M':>13}"
    f"{'6M':>13}"
    f"{'1Y':>13}"
    f"{'3Y':>13}"
)

print("-" * 100)

for group_name in groups:

    changes = timeframe_changes[group_name]

    print(
        f"{group_name:<20}"
        f"{changes['1W']:>+13,.0f}"
        f"{changes['1M']:>+13,.0f}"
        f"{changes['3M']:>+13,.0f}"
        f"{changes['6M']:>+13,.0f}"
        f"{changes['1Y']:>+13,.0f}"
        f"{changes['3Y']:>+13,.0f}"
    )

print("=" * 100)


# ============================================================
# 15. INTERACTIVE CHART SELECTION
# ============================================================

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

print("\nChoose chart:\n")

print("1 - Dealer")
print("2 - Asset Manager")
print("3 - Leveraged Funds")
print("4 - Compare All")

chart_choice = input("\nEnter chart: ")

print("\nChoose period:\n")

print("1 - 6 Months")
print("2 - 1 Year")
print("3 - 3 Years")

period_choice = input("\nEnter period: ")


# ============================================================
# CHART SETTINGS
# ============================================================

CHARTS = {
    "1": {
        "name": "Dealer",
        "column": "dealer_net"
    },

    "2": {
        "name": "Asset Manager",
        "column": "asset_manager_net"
    },

    "3": {
        "name": "Leveraged Funds",
        "column": "leveraged_funds_net"
    }
}


# ============================================================
# FORMAT Y AXIS
# ============================================================

def format_position(value, position):

    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"

    if abs(value) >= 1_000:
        return f"{value / 1_000:.0f}K"

    return f"{value:.0f}"

# ============================================================
# SELECT CHART PERIOD
# ============================================================

if period_choice == "1":
    chart_start_date = latest_report_date - pd.DateOffset(months=6)
    period_name = "6 Months"

elif period_choice == "2":
    chart_start_date = latest_report_date - pd.DateOffset(years=1)
    period_name = "1 Year"

elif period_choice == "3":
    chart_start_date = latest_report_date - pd.DateOffset(years=3)
    period_name = "3 Years"

else:
    print("\nERROR: Invalid period selection.")
    raise SystemExit


chart_df = df_3y[
    df_3y["report_date_as_yyyy_mm_dd"] >= chart_start_date
].copy()

# ============================================================
# CREATE CHART
# ============================================================

plt.figure(figsize=(14, 7))


# Individual group
if chart_choice in CHARTS:

    chart = CHARTS[chart_choice]

    group_name = chart["name"]
    column = chart["column"]

    plt.plot(
        chart_df["report_date_as_yyyy_mm_dd"],
        chart_df[column],
        linewidth=2,
        label=group_name
    )

    current_value = chart_df[column].iloc[-1]

    # 3Y historical mean
    historical_mean = df_3y[column].mean()

    plt.scatter(
        chart_df["report_date_as_yyyy_mm_dd"].iloc[-1],
        current_value,
        s=60,
        zorder=5
    )

    # 3Y historical mean line
    plt.axhline(
        y=historical_mean,
        linestyle="--",
        linewidth=1.5,
        label=f"3Y Mean: {historical_mean:,.0f}"
    )

    plt.title(
        f"{MARKET_NAME} — {group_name} Net Position ({period_name})"
    )

    plt.legend()


# Compare all groups
elif chart_choice == "4":

    plt.plot(
        chart_df["report_date_as_yyyy_mm_dd"],
        chart_df["dealer_net"],
        linewidth=2,
        label="Dealer"
    )

    plt.plot(
        chart_df["report_date_as_yyyy_mm_dd"],
        chart_df["asset_manager_net"],
        linewidth=2,
        label="Asset Manager"
    )

    plt.plot(
        chart_df["report_date_as_yyyy_mm_dd"],
        chart_df["leveraged_funds_net"],
        linewidth=2,
        label="Leveraged Funds"
    )

    plt.title(
        f"{MARKET_NAME} — COT Net Positions ({period_name})"
    )

    plt.legend()


else:

    print("\nERROR: Invalid chart selection.")
    raise SystemExit


# ============================================================
# CHART DESIGN
# ============================================================

plt.axhline(
    y=0,
    linewidth=1
)

plt.xlabel("Report Date")
plt.ylabel("Net Position")

plt.gca().yaxis.set_major_formatter(
    FuncFormatter(format_position)
)

plt.grid(
    True,
    alpha=0.25
)

plt.tight_layout()

plt.show()