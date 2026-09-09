from pathlib import Path
from datetime import date, timedelta

import pandas as pd
import yfinance as yf


BASE_DIR = Path(__file__).resolve().parent.parent

ASSET_PATH = BASE_DIR / "data" / "raw" / "assets.csv"
OUTPUT_PATH = BASE_DIR / "data" / "cache" / "prices.csv"

START_DATE = "2026-01-01"
END_DATE = (date.today() + timedelta(days=1)).isoformat()


def fetch_prices():
    assets = pd.read_csv(ASSET_PATH)

    result = []

    for _, asset in assets.iterrows():
        asset_id = asset["asset_id"]
        symbol = asset["symbol"]

        print(f"Fetching {symbol}...")

        ticker = yf.Ticker(symbol)

        history = ticker.history(
            start=START_DATE,
            end=END_DATE,
            auto_adjust=False
        )

        if history.empty:
            print(f"WARNING: no data for {symbol}")
            continue

        history = history.reset_index()
        history = history.dropna(subset=["Close"])
        history = history[history["Close"] > 0]

        for _, row in history.iterrows():
            result.append({
                "price_date": row["Date"].date().isoformat(),
                "asset_id": asset_id,
                "close_price": float(row["Close"])
            })

    prices = pd.DataFrame(result)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(OUTPUT_PATH, index=False)

    print()
    print("Price data saved.")
    print(f"Rows: {len(prices)}")
    print(prices.head())


if __name__ == "__main__":
    fetch_prices()