import requests
import pandas as pd
from datetime import datetime, timedelta

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
print("\nDownloading COT data...")

# ============================================================
# 3. DOWNLOAD 3 YEARS OF DATA
# ============================================================

today = datetime.now()
three_years_ago = today - timedelta(days=365 * 3)

start_date = three_years_ago.strftime("%Y-%m-%dT00:00:00")

params = {
    "$limit": 500,
    "$where": (
        f"market_and_exchange_names='{MARKET}' "
        f"AND report_date_as_yyyy_mm_dd >= '{start_date}'"
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
# 4. PREPARE DATA
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
    df[column] = pd.to_numeric(df[column])

# ============================================================
# 5. CALCULATE NET POSITIONS
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
# 6. PERCENTILE
# ============================================================

def calculate_percentile(series):

    current_value = series.iloc[-1]

    values_below = (series < current_value).sum()
    values_equal = (series == current_value).sum()

    percentile = (
        values_below + 0.5 * values_equal
    ) / len(series) * 100

    return percentile

# ============================================================
# 7. Z-SCORE
# ============================================================

def calculate_zscore(series):

    current_value = series.iloc[-1]

    average = series.mean()

    standard_deviation = series.std(ddof=0)

    if standard_deviation == 0:
        return 0.0

    return (
        current_value - average
    ) / standard_deviation

# ============================================================
# 8. CURRENT REPORT
# ============================================================

current = df.iloc[-1]

# ============================================================
# 9. GROUP SETTINGS
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
# 10. CALCULATE RESULTS
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
        df[cols["net"]]
    )

    zscore = calculate_zscore(
        df[cols["net"]]
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
# 11. DISPLAY RESULTS
# ============================================================

report_date = current[
    "report_date_as_yyyy_mm_dd"
].strftime("%Y-%m-%d")

print("\n" + "=" * 135)

print(f"{MARKET_NAME} — COT ANALYZER")

print("=" * 135)

print(f"Report date: {report_date}")
print(f"3Y reports analyzed: {len(df)}")

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