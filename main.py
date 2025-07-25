import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os

# ✅ Load ASX200 tickers from local cache file only
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

# ✅ DM9/DM13 logic (replicated from Pine Script)
def compute_dm_signals(df):
    close = df["Close"].values
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

    DM9Top = any(t == 9 for t in TDUp)
    DM13Top = any(t == 13 for t in TDUp)
    DM9Bot = any(t == 9 for t in TDDn)
    DM13Bot = any(t == 13 for t in TDDn)

    return DM9Top, DM13Top, DM9Bot, DM13Bot

def main():
    tickers = fetch_asx200_tickers()
    print(f"📈 Scanning {len(tickers)} tickers for DM9/DM13 signals...")

    signals_found = []

    # Use yesterday's date to get most recent close (handle weekends/holidays)
    end_date = datetime.utcnow().date() - timedelta(days=1)
    start_date = end_date - timedelta(days=30)

    for ticker in tickers:
        try:
            df = yf.download(ticker, start=start_date.isoformat(), end=end_date.isoformat(), progress=False)
            if df.empty:
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
            print(f"Failed to get ticker '{ticker}' reason: {e}")

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

            print(f" - {signal['Ticker']}: {', '.join(flags)}")
    else:
        print(f"🚫 No signals found today.")

if __name__ == "__main__":
    main()
