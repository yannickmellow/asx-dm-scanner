# main.py

import yfinance as yf
import pandas as pd
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import os

# ✅ Fetch ASX200 tickers
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
    DM9 = [False] * length
    DM13 = [False] * length
    DM9B = [False] * length
    DM13B = [False] * length

    for i in range(4, length):
        TD[i] = TD[i - 1] + 1 if close[i] > close[i - 4] else 0
        TS[i] = TS[i - 1] + 1 if close[i] < close[i - 4] else 0

    last_td_reset = 0
    last_ts_reset = 0

    for i in range(1, length):
        if TD[i] < TD[i - 1]:
            last_td_reset = i
        if TS[i] < TS[i - 1]:
            last_ts_reset = i

        TDUp[i] = TD[i] - TD[last_td_reset] if last_td_reset < i else 0
        TDDn[i] = TS[i] - TS[last_ts_reset] if last_ts_reset < i else 0

        DM9[i] = TDUp[i] == 9
        DM13[i] = TDUp[i] == 13
        DM9B[i] = TDDn[i] == 9
        DM13B[i] = TDDn[i] == 13

    return DM9[-1], DM13[-1], DM9B[-1], DM13B[-1]

# ✅ Scan and output signals
def scan_asx200():
    tickers = fetch_asx200_tickers()
    print(f"📈 Scanning {len(tickers)} tickers for DM9/DM13 signals...\n")

    results = []

    for ticker in tickers:
        try:
            df = yf.download(ticker, period="30d", interval="1d", progress=False)
            if df.empty or "Close" not in df.columns:
                continue

            DM9, DM13, DM9B, DM13B = compute_dm_signals(df)
            if DM9 or DM13 or DM9B or DM13B:
                result = {
                    "Ticker": ticker,
                    "DM9": DM9,
                    "DM13": DM13,
                    "DM9B": DM9B,
                    "DM13B": DM13B,
                }
                results.append(result)

        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")

    # Output results
    if results:
        df_out = pd.DataFrame(results)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        print(f"\n📋 Signals found at {timestamp}:\n")
        print(df_out.to_string(index=False))
    else:
        print("🚫 No signals found today.")

# ✅ Run script
if __name__ == "__main__":
    scan_asx200()
