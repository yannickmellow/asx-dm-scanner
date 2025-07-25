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

# DM9/DM13 logic (replicated from Pine Script)
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
        TS[i] = TS[i-1] + 1 if close[i] < close[i-4] else 0

    # Helper: find last reset
    def valuewhen_reset(arr, idx):
        for j in range(idx - 1, 0, -1):
            if arr[j] < arr[j - 1]:
                return arr[j]
        return 0

    for i in range(4, length):
        TDUp[i] = TD[i] - valuewhen_reset(TD, i)
        TDDn[i] = TS[i] - valuewhen_reset(TS, i)

    # Check that last bar is from yesterday
    last_bar_date = df["date"].iloc[-1].date()
    expected_date = datetime.utcnow().date() - timedelta(days=1)
    if last_bar_date != expected_date:
        return False, False, False, False

    # Only trigger if yesterday's bar completed the sequence
    i = length - 1
    DM9Top = TDUp[i] == 9
    DM13Top = TDUp[i] == 13
    DM9Bot = TDDn[i] == 9
    DM13Bot = TDDn[i] == 13

    return DM9Top, DM13Top, DM9Bot, DM13Bot

def main():
    tickers = fetch_asx200_tickers()
    print(f"📈 Scanning {len(tickers)} tickers for DM9/DM13 signals...")

    signals_found = []

    for ticker in tickers:
        try:
            tk = Ticker(ticker)
            hist = tk.history(period='1mo', interval='1d')
            if hist.empty:
                continue

            # yahooquery returns MultiIndex if multiple tickers
            if isinstance(hist.index, pd.MultiIndex):
                df = hist.xs(ticker, level=0)
            else:
                df = hist

            df = df.reset_index()
            df.columns = [c.lower() for c in df.columns]

            # Drop any future bars (e.g. today's)
            df = df[df['date'] < pd.Timestamp(datetime.utcnow().date())]

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

            print(f" - {signal['Ticker']}: {', '.join(flags)}")
    else:
        print(f"🚫 No signals found for yesterday's trading session.")

if __name__ == "__main__":
    main()
