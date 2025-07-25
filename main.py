import pandas as pd
from datetime import datetime, timedelta
import os
from yahooquery import Ticker

# Load ASX200 tickers from local cache file only
def fetch_asx200_tickers():
    cache_file = "asx200_cache.txt"

    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            tickers = [line.strip() for line in f if line.strip()]
            print(f"✅ Loaded {len(tickers)} tickers from cache file.")
            return tickers
    else:
        print("❌ Ticker cache file not found!")
        return []

# Helper function to replicate PineScript's valuewhen(condition) in Python
def valuewhen_condition(arr):
    length = len(arr)
    last_vals = [0] * length
    last_value = 0
    for i in range(1, length):
        if arr[i] < arr[i-1]:
            last_value = arr[i]
        last_vals[i] = last_value
    return last_vals

# DM9/DM13 logic adapted from PineScript
def compute_dm_signals(df):
    close = df["close"].values
    length = len(close)
    if length < 20:
        return False, False, False, False

    TD = [0] * length
    TS = [0] * length

    for i in range(4, length):
        TD[i] = TD[i-1] + 1 if close[i] > close[i-4] else 0
        TS[i] = TS[i-1] + 1 if close[i] < close[i-4] else 0

    TD_valwhen = valuewhen_condition(TD)
    TS_valwhen = valuewhen_condition(TS)

    TDUp = [TD[i] - TD_valwhen[i] for i in range(length)]
    TDDn = [TS[i] - TS_valwhen[i] for i in range(length)]

    # We want to detect signals ONLY on the last available trading day
    last_TDUp = TDUp[-1]
    last_TDDn = TDDn[-1]

    DM13Top = last_TDUp == 13
    DM9Top = last_TDUp == 9 and not DM13Top

    DM13Bot = last_TDDn == 13
    DM9Bot = last_TDDn == 9 and not DM13Bot

    return DM9Top, DM13Top, DM9Bot, DM13Bot

def main():
    tickers = fetch_asx200_tickers()
    print(f"📈 Scanning {len(tickers)} tickers for DM9/DM13 signals...")

    signals_found = []

    # We consider "yesterday" as the day to detect signals for
    end_date = datetime.utcnow().date() - timedelta(days=1)
    start_date = end_date - timedelta(days=30)

    for ticker in tickers:
        try:
            tk = Ticker(ticker)
            hist = tk.history(period='1mo', interval='1d')
            if hist.empty:
                continue

            # Handle multiindex from yahooquery for multiple tickers
            if isinstance(hist.index, pd.MultiIndex):
                df = hist.xs(ticker, level=0)
            else:
                df = hist

            df = df.reset_index()
            df.columns = [c.lower() for c in df.columns]

            # Convert dates to date objects
            df["date"] = pd.to_datetime(df["date"]).dt.date

            last_date = df["date"].iloc[-1]

            # Accept last_date if it is <= expected end_date (can be before due to weekends/holidays)
            if last_date > end_date:
                print(f"⚠️ Warning: Last date {last_date} beyond expected {end_date} for {ticker}, skipping.")
                continue

            DM9Top, DM13Top, DM9Bot, DM13Bot = compute_dm_signals(df)

            if DM9Top or DM13Top or DM9Bot or DM13Bot:
                signals_found.append({
                    "Ticker": ticker,
                    "DM9Top": DM9Top,
                    "DM13Top": DM13Top,
                    "DM9Bot": DM9Bot,
                    "DM13Bot": DM13Bot,
                    "Date": last_date,
                })

        except Exception as e:
            print(f"⚠️ Skipping ticker '{ticker}' due to error: {e}")

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    if signals_found:
        print(f"📋 Signals found at {now_str}:")
        for signal in signals_found:
            flags = []
            if signal["DM9Top"]:
                flags.append("DM9Top")
            if signal["DM13Top"]:
                flags.append("DM13Top")
            if signal["DM9Bot"]:
                flags.append("DM9Bot")
            if signal["DM13Bot"]:
                flags.append("DM13Bot")

            print(f" - {signal['Ticker']} ({signal['Date']}): {', '.join(flags)}")
    else:
        print(f"🚫 No signals found today.")

if __name__ == "__main__":
    main()
