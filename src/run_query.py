from pathlib import Path
import sqlite3

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "portfolio.db"


def run_query(sql):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(sql, conn)


if __name__ == "__main__":

    sql = """
    SELECT
        ROUND(SUM(exposure_pct), 2) AS total_pct
    FROM (
        SELECT
            SUM(market_value_krw)
            * 100.0
            /
            (
                SELECT SUM(market_value_krw)
                FROM valuation_summary
            ) AS exposure_pct
        FROM valuation_summary
        GROUP BY asset_class
    );
    """

    result = run_query(sql)
    print(result.to_string(index=False))