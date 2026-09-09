from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

PRICE_PATH = BASE_DIR / "data" / "cache" / "prices.csv"
OUTPUT_PATH = BASE_DIR / "data" / "raw" / "trades.csv"


TRADE_PLAN = [
    ("T001", "2026-01-12", "A001", "BUY", 100),
    ("T002", "2026-03-09", "A001", "BUY", 50),
    ("T003", "2026-05-11", "A001", "BUY", 30),
    ("T004", "2026-07-13", "A001", "SELL", 40),

    ("T005", "2026-01-19", "A002", "BUY", 150),
    ("T006", "2026-03-16", "A002", "BUY", 70),
    ("T007", "2026-05-18", "A002", "BUY", 50),
    ("T008", "2026-07-20", "A002", "SELL", 60),

    ("T009", "2026-01-26", "A003", "BUY", 120),
    ("T010", "2026-03-23", "A003", "BUY", 60),
    ("T011", "2026-05-25", "A003", "BUY", 40),
    ("T012", "2026-07-27", "A003", "SELL", 50),

    ("T013", "2026-02-02", "A004", "BUY", 60),
    ("T014", "2026-04-06", "A004", "BUY", 30),
    ("T015", "2026-06-08", "A004", "BUY", 20),
    ("T016", "2026-08-03", "A004", "SELL", 25),

    ("T017", "2026-02-09", "A005", "BUY", 100),
    ("T018", "2026-04-13", "A005", "BUY", 50),
    ("T019", "2026-06-15", "A005", "BUY", 30),
    ("T020", "2026-08-10", "A005", "SELL", 40),

    ("T021", "2026-02-16", "A006", "BUY", 100),
    ("T022", "2026-04-20", "A006", "BUY", 50),
    ("T023", "2026-06-22", "A006", "BUY", 30),
    ("T024", "2026-08-17", "A006", "SELL", 40),

    ("T025", "2026-02-23", "A007", "BUY", 40),
    ("T026", "2026-04-27", "A007", "BUY", 20),
    ("T027", "2026-06-29", "A007", "BUY", 15),
    ("T028", "2026-08-24", "A007", "SELL", 15),
]


def generate_trades():
    prices = pd.read_csv(PRICE_PATH)
    prices["price_date"] = pd.to_datetime(prices["price_date"])

    trades = []

    for trade_id, planned_date, asset_id, trade_type, quantity in TRADE_PLAN:

        planned_date = pd.Timestamp(planned_date)

        available_prices = prices[
            (prices["asset_id"] == asset_id)
            & (prices["price_date"] >= planned_date)
        ].sort_values("price_date")

        if available_prices.empty:
            raise ValueError(
                f"No market price found for {trade_id}, {asset_id}"
            )

        # 휴장일인 경우 예정일 이후 첫 거래일 사용
        market_row = available_prices.iloc[0]

        trades.append({
            "trade_id": trade_id,
            "trade_date": market_row["price_date"].date().isoformat(),
            "asset_id": asset_id,
            "trade_type": trade_type,
            "quantity": quantity,
            "trade_price": float(market_row["close_price"])
        })

    trades_df = pd.DataFrame(trades)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    trades_df.to_csv(OUTPUT_PATH, index=False)

    print("Trades generated.")
    print(f"Rows: {len(trades_df)}")
    print(trades_df.head())


if __name__ == "__main__":
    generate_trades()