from pathlib import Path
import sqlite3

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "db" / "portfolio.db"
SCHEMA_PATH = BASE_DIR / "sql" / "schema.sql"

ASSET_PATH = BASE_DIR / "data" / "raw" / "assets.csv"
TRADE_PATH = BASE_DIR / "data" / "raw" / "trades.csv"
PRICE_PATH = BASE_DIR / "data" / "cache" / "prices.csv"
FX_PATH = BASE_DIR / "data" / "cache" / "fx_rates.csv"


def load_csv(path):
    return pd.read_csv(path)


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    assets = load_csv(ASSET_PATH)
    trades = load_csv(TRADE_PATH)
    prices = load_csv(PRICE_PATH)
    fx_rates = load_csv(FX_PATH)

    with sqlite3.connect(DB_PATH) as conn:

        conn.execute("PRAGMA foreign_keys = ON")

        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        conn.executescript(schema_sql)

        assets.to_sql(
            "asset",
            conn,
            if_exists="append",
            index=False
        )

        trades.to_sql(
            "trade",
            conn,
            if_exists="append",
            index=False
        )

        prices.to_sql(
            "price",
            conn,
            if_exists="append",
            index=False
        )

        fx_rates.to_sql(
            "fx_rate",
            conn,
            if_exists="append",
            index=False
        )

        conn.commit()

        print("Database initialized.")
        print(f"DB: {DB_PATH}")

        tables = [
            "asset",
            "trade",
            "price",
            "fx_rate"
        ]

        print()
        print("Row counts")

        for table in tables:
            count = conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

            print(f"{table:10s}: {count}")


if __name__ == "__main__":
    init_db()