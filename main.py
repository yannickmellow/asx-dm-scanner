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
        TDUp[i] = TD[i] - (TD[i-1] if TD[i-1] < TD[i] else 0)

        TS[i] = TS[i-1] + 1 if close[i] < close[i-4] else 0
        TDDn[i] = TS[i] - (TS[i-1] if TS[i-1] < TS[i] else 0)

    DM9Top = any(t == 9 for t in TDUp)
    DM13Top = any(t == 13 for t in TDUp)
    DM9Bot = any(t == 9 for t in TDDn)
    DM13Bot = any(t == 13 for t in TDDn)

    # Also return arrays so we can identify if the signal happened on the last date
    return DM9Top, DM13Top, DM9Bot, DM13Bot, TDUp, TDDn

def main():
    tickers = fetch_asx200_tickers()
    print(f"📈 Scanning {len(tickers)} tickers for DM9/DM13 signals from previous trading day...")

    signals_found = []

    # Set dates for 30 days lookback and previous day detection
    end_date = datetime.utcnow().date() - timedelta(days=1)
    start_date = end_date - timedelta(days=30)

    for ticker in tickers:
        try:
            tk = Ticker(ticker)
            hist = tk.history(period='1mo', interval='1d')
            if hist.empty:
                continue

            if isinstance(hist.index, pd.MultiIndex):
                df = hist.xs(ticker, level=0)
            else:
                df = hist

            df = df.reset_index()
            df.columns = [c.lower() for c in df.columns]

            # Fix timezone issue: remove tz info if present
            df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
            last_date = df["date"].iloc[-1].date()

            if last_date > end_date:
                print(f"⚠️ Warning: Last date {last_date} beyond expected {end_date} for {ticker}, skipping.")
                continue

            DM9Top, DM13Top, DM9Bot, DM13Bot, TDUp, TDDn = compute_dm_signals(df)

            # Only check if signal triggered on last date
            # Last index
            i = len(df) - 1
            signal_on_last = {
                "DM9Top": TDUp[i] == 9,
                "DM13Top": TDUp[i] == 13,
                "DM9Bot": TDDn[i] == 9,
                "DM13Bot": TDDn[i] == 13,
            }

            if any(signal_on_last.values()):
                signals_found.append({
                    "Ticker": ticker,
                    **signal_on_last
                })

        except Exception as e:
            print(f"⚠️ Skipping ticker '{ticker}' due to error: {e}")

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    if signals_found:
        print(f"📋 Signals found on previous trading day ({end_date}) at {now_str}:")
        for signal in signals_found:
            flags = [key for key, val in signal.items() if key != "Ticker" and val]
            print(f" - {signal['Ticker']}: {', '.join(flags)}")
    else:
        print(f"🚫 No signals found on previous trading day ({end_date}).")

if __name__ == "__main__":
    main()
