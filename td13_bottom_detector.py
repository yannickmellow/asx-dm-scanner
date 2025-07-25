import yfinance as yf
import pandas as pd
import numpy as np

def calculate_td13_bottom(df):
    """
    Calculate TD13 bottom signals according to the Pine Script logic.
    Input df must have a 'Close' column.
    """

    TS = np.zeros(len(df), dtype=int)

    for i in range(len(df)):
        if i >= 4:
            if df['Close'].iloc[i] < df['Close'].iloc[i - 4]:
                TS[i] = TS[i - 1] + 1
            else:
                TS[i] = 0
        else:
            TS[i] = 0

    last_drop_TS_value = 0
    TDDn = np.zeros(len(df), dtype=int)

    for i in range(len(df)):
        if i == 0:
            TDDn[i] = TS[i]
            continue

        if TS[i] < TS[i - 1]:
            last_drop_TS_value = TS[i]

        TDDn[i] = TS[i] - last_drop_TS_value

    df['TD13Bottom'] = TDDn == 13
    return df

def main():
    ticker = "COST"
    print(f"Downloading data for {ticker}...")
    df = yf.download(ticker, period="1y", interval="1d")  # 1 year daily data

    if df.empty:
        print(f"No data found for ticker {ticker}.")
        return

    df = calculate_td13_bottom(df)

    td13_bottom_dates = df.index[df['TD13Bottom']].to_list()
    if td13_bottom_dates:
        print(f"TD13 Bottom signals detected on these dates for {ticker}:")
        for date in td13_bottom_dates:
            print(date.date())
    else:
        print(f"No TD13 Bottom signals detected for {ticker} in the last year.")

if __name__ == "__main__":
    main()
