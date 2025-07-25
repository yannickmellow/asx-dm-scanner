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

# DM9/DM13 logic, check only if triggered on last trading day
def compute_dm_signals(df):
    close = df["close"].values
    length = len(close)
    if length < 20:
        return False, False, False, False

    TD = [0] * length
    TDUp = [0] * length
    TS = [0] * length
    TDDn = [0] * length

    for i in range(4, length):
        TD[i] = TD[i-1] + 1 if close[i] > close[i-4] else 0
        TDUp[i] = TD[i] - (TD[i-1] if TD[i-1] < TD[i] else 0)

        TS[i] = TS[i-1] + 1 if close[i] < close[i-4] else 0
        TDDn[i] = TS[i] - (TS[i-1] if TS[i-1] < TS[i] else 0)

    # Signals only if triggered on last day
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

    # Use last 30 calendar days to cover 20+ trading days
    end_date = datetime.utcnow().date() - timedelta(days=1)  # yesterday
    start_date = end_date - timedelta(days=30)

    for ticker in tickers:
        try:
            tk = Ticker(ticker)
            hist = tk.history(period='1mo', interval='1d')
            if hist.empty:
                continue

            # If multiple tickers returned, filter for this ticker
            if isinstance(hist.index, pd.MultiIndex):
                df = hist.xs(ticker, level=0)
            else:
                df = hist

            df = df.reset_index()
            # Normalize columns to lowercase
            df.columns = [c.lower() for c in df.columns]

            # Sort oldest to newest (usually already sorted, but safe)
            df = df.sort_values(by="date").reset_index(drop=True)

            # Only proceed if we have data for the last trading day (end_date)
            if pd.to_datetime(df["date"].iloc[-1]).date() != end_date:
                print(f"⚠️ Warning: Last trading day data missing for {ticker}, skipping.")
                continue

            DM9Top, DM13Top, DM9Bot, DM13Bot = compute_dm_signals(df)

            if DM9Top or DM13Top or DM9Bot or DM13Bot:
                signals_found.append({
                    "Ticker": ticker,
                    "DM9Top": DM9Top,
                    "DM13Top": DM13Top,
                    "DM9Bot": DM9Bot,
                    "DM13Bot": DM13Bot,
                })

        except Exception as e:
            print(f"⚠️ Skipping ticker '{ticker}' due to error: {e}")

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    if signals_found:
        print(f"📋 Signals triggered on {end_date} (yesterday) at {now_str}:")
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

            print(f" - {signal['Ticker']}: {', '.join(flags)}")
    else:
        print(f"🚫 No TD9/TD13 signals triggered on {end_date}.")

if __name__ == "__main__":
    main()
