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

# DM9/DM13 logic — triggered on last bar only
def compute_dm_signals(df, timeframe="daily"):
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

    def valuewhen_reset(arr, idx):
        for j in range(idx - 1, 0, -1):
            if arr[j] < arr[j - 1]:
                return arr[j]
        return 0

    for i in range(4, length):
        TDUp[i] = TD[i] - valuewhen_reset(TD, i)
        TDDn[i] = TS[i] - valuewhen_reset(TS, i)

    # Compare only the last bar to the previous full trading period
    last_bar_date = df["date"].iloc[-1].date()
    if timeframe == "daily":
        expected_date = datetime.utcnow().date() - timedelta(days=1)
    elif timeframe == "weekly":
        expected_date = (datetime.utcnow() - timedelta(days=datetime.utcnow().weekday() + 2)).date()  # previous Friday
    else:
        return False, False, False, False

    if last_bar_date != expected_date:
        return False, False, False, False

    i = length - 1
    DM9Top = TDUp[i] == 9
    DM13Top = TDUp[i] == 13
    DM9Bot = TDDn[i] == 9
    DM13Bot = TDDn[i] == 13

    return DM9Top, DM13Top, DM9Bot, DM13Bot

def scan_signals(ticker, interval, timeframe_label):
    try:
        tk = Ticker(ticker)
        hist = tk.history(period='6mo', interval=interval)
        if hist.empty:
            return None

        if isinstance(hist.index, pd.MultiIndex):
            df = hist.xs(ticker, level=0)
        else:
            df = hist

        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]

        # Remove today's partial bar
        df = df[df["date"] < pd.Timestamp(datetime.utcnow().date())]
        if df.empty:
            return None

        return compute_dm_signals(df, timeframe_label)
    except Exception as e:
        print(f"⚠️ Skipping {ticker} [{interval}] due to error: {e}")
        return None

def main():
    tickers = fetch_asx200_tickers()
    print(f"📊 Scanning {len(tickers)} tickers for daily and weekly DM9/DM13 signals...\n")

    signals_found = []

    for ticker in tickers:
        daily = scan_signals(ticker, interval="1d", timeframe_label="daily")
        weekly = scan_signals(ticker, interval="1wk", timeframe_label="weekly")

        if daily is None and weekly is None:
            continue

        daily_flags = []
        weekly_flags = []

        if daily:
            d9t, d13t, d9b, d13b = daily
            if d9t: daily_flags.append("DM9Top")
            if d13t: daily_flags.append("DM13Top")
            if d9b: daily_flags.append("DM9Bot")
            if d13b: daily_flags.append("DM13Bot")

        if weekly:
            w9t, w13t, w9b, w13b = weekly
            if w9t: weekly_flags.append("DM9Top (W)")
            if w13t: weekly_flags.append("DM13Top (W)")
            if w9b: weekly_flags.append("DM9Bot (W)")
            if w13b: weekly_flags.append("DM13Bot (W)")

        if daily_flags or weekly_flags:
            signals_found.append({
                "Ticker": ticker,
                "Daily": daily_flags,
                "Weekly": weekly_flags,
            })

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    if signals_found:
        print(f"✅ Signals found as of {now_str}:\n")
        for sig in signals_found:
            if sig["Daily"]:
                print(f"📅 {sig['Ticker']} -- {', '.join(sig['Daily'])}")
            if sig["Weekly"]:
                print(f"🗓️ {sig['Ticker']} -- {', '.join(sig['Weekly'])}")
    else:
        print("🚫 No signals found for daily or weekly bars.")

if __name__ == "__main__":
    main()
