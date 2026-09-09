from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "db" / "portfolio.db"
QUERY_PATH = BASE_DIR / "sql" / "portfolio_queries.sql"


def create_views():
    with sqlite3.connect(DB_PATH) as conn:

        with open(
            QUERY_PATH,
            "r",
            encoding="utf-8"
        ) as f:
            sql = f.read()

        conn.executescript(sql)
        conn.commit()

    print("Views created.")


if __name__ == "__main__":
    create_views()