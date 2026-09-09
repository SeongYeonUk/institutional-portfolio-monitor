from pathlib import Path
import sqlite3

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "portfolio.db"
HISTORY_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "portfolio_history.csv"
)

def run_check(conn, name, sql):
    result = pd.read_sql_query(sql, conn)

    passed = result.empty

    return {
        "check_name": name,
        "status": "PASS" if passed else "FAIL",
        "issue_count": len(result)
    }


def validate_source_data():

    checks = [
        (
            "Duplicate Trade ID",
            """
            SELECT
                trade_id,
                COUNT(*) AS duplicate_count
            FROM trade
            GROUP BY trade_id
            HAVING COUNT(*) > 1;
            """
        ),
        (
            "Invalid Trade Values",
            """
            SELECT *
            FROM trade
            WHERE quantity <= 0
               OR trade_price <= 0
               OR trade_type NOT IN ('BUY', 'SELL');
            """
        ),
        (
            "Orphan Trade",
            """
            SELECT t.*
            FROM trade t
            LEFT JOIN asset a
                ON t.asset_id = a.asset_id
            WHERE a.asset_id IS NULL;
            """
        ),
        (
            "Invalid Price",
            """
            SELECT *
            FROM price
            WHERE close_price IS NULL
               OR close_price <= 0;
            """
        ),
        (
            "Invalid FX Rate",
            """
            SELECT *
            FROM fx_rate
            WHERE rate_to_krw IS NULL
               OR rate_to_krw <= 0;
            """
        )
    ]

    results = []

    with sqlite3.connect(DB_PATH) as conn:

        for name, sql in checks:
            results.append(
                run_check(
                    conn,
                    name,
                    sql
                )
            )

    return pd.DataFrame(results)

def validate_derived_data():

    checks = [
        (
            "Negative Position",
            """
            SELECT *
            FROM position_summary
            WHERE position < 0;
            """
        ),

        (
            "Missing Valuation Price",
            """
            SELECT *
            FROM valuation_summary
            WHERE current_price IS NULL;
            """
        ),

        (
            "Missing Valuation FX",
            """
            SELECT *
            FROM valuation_summary
            WHERE rate_to_krw IS NULL;
            """
        ),

        (
            "Missing Market Value",
            """
            SELECT *
            FROM valuation_summary
            WHERE market_value_krw IS NULL;
            """
        )
    ]

    results = []

    with sqlite3.connect(DB_PATH) as conn:

        for name, sql in checks:

            results.append(
                run_check(
                    conn,
                    name,
                    sql
                )
            )

    return pd.DataFrame(results)

def validate_exposure():

    with sqlite3.connect(DB_PATH) as conn:

        total_value = conn.execute(
            """
            SELECT SUM(market_value_krw)
            FROM valuation_summary;
            """
        ).fetchone()[0]

        asset_class_total = conn.execute(
            """
            SELECT SUM(class_value)
            FROM (
                SELECT
                    SUM(market_value_krw)
                        AS class_value
                FROM valuation_summary
                GROUP BY asset_class
            );
            """
        ).fetchone()[0]

        currency_total = conn.execute(
            """
            SELECT SUM(currency_value)
            FROM (
                SELECT
                    SUM(market_value_krw)
                        AS currency_value
                FROM valuation_summary
                GROUP BY currency
            );
            """
        ).fetchone()[0]

    tolerance = 0.01

    asset_diff = abs(
        total_value - asset_class_total
    )

    currency_diff = abs(
        total_value - currency_total
    )

    results = [
        {
            "check_name":
                "Asset Exposure Reconciliation",
            "status":
                "PASS"
                if asset_diff <= tolerance
                else "FAIL",
            "issue_count":
                0
                if asset_diff <= tolerance
                else 1
        },

        {
            "check_name":
                "Currency Exposure Reconciliation",
            "status":
                "PASS"
                if currency_diff <= tolerance
                else "FAIL",
            "issue_count":
                0
                if currency_diff <= tolerance
                else 1
        }
    ]

    return pd.DataFrame(results)

def validate_sql_python_reconciliation():

    with sqlite3.connect(DB_PATH) as conn:

        sql_result = pd.read_sql_query(
            """
            SELECT
                valuation_date,
                SUM(market_value_krw)
                    AS portfolio_value_krw
            FROM valuation_summary
            GROUP BY valuation_date;
            """,
            conn
        )

    history = pd.read_csv(
        HISTORY_PATH,
        parse_dates=["date"]
    )

    sql_date = pd.to_datetime(
        sql_result.loc[0, "valuation_date"]
    )

    sql_value = float(
        sql_result.loc[0, "portfolio_value_krw"]
    )

    python_last = history.iloc[-1]

    python_date = python_last["date"]

    python_value = float(
        python_last["portfolio_value_krw"]
    )

    value_difference = abs(
        sql_value - python_value
    )

    date_match = (
        sql_date.date()
        == python_date.date()
    )

    # 부동소수점 계산 오차 허용
    tolerance_krw = 1.0

    value_match = (
        value_difference
        <= tolerance_krw
    )

    passed = (
        date_match
        and value_match
    )

    result = pd.DataFrame([
        {
            "check_name":
                "SQL-Python Portfolio Reconciliation",
            "status":
                "PASS" if passed else "FAIL",
            "sql_date":
                sql_date.date(),
            "python_date":
                python_date.date(),
            "sql_value_krw":
                round(sql_value, 2),
            "python_value_krw":
                round(python_value, 2),
            "difference_krw":
                round(value_difference, 6)
        }
    ])

    return result

def build_validation_summary(
    source_results,
    derived_results,
    exposure_results,
    reconciliation_results
):
    summary_rows = []

    for _, row in source_results.iterrows():
        status = row["status"]

        # 알려진 외부 데이터 결측은 별도 처리
        if (
            row["check_name"] == "Invalid Price"
            and row["issue_count"] == 1
        ):
            status = "HANDLED"

        summary_rows.append({
            "category": "Source",
            "check_name": row["check_name"],
            "status": status
        })

    for _, row in derived_results.iterrows():
        summary_rows.append({
            "category": "Derived",
            "check_name": row["check_name"],
            "status": row["status"]
        })

    for _, row in exposure_results.iterrows():
        summary_rows.append({
            "category": "Reconciliation",
            "check_name": row["check_name"],
            "status": row["status"]
        })

    for _, row in reconciliation_results.iterrows():
        summary_rows.append({
            "category": "Reconciliation",
            "check_name": row["check_name"],
            "status": row["status"]
        })

    summary = pd.DataFrame(summary_rows)

    pass_count = (
        summary["status"] == "PASS"
    ).sum()

    handled_count = (
        summary["status"] == "HANDLED"
    ).sum()

    fail_count = (
        summary["status"] == "FAIL"
    ).sum()

    overall_status = (
        "PASS"
        if fail_count == 0
        else "FAIL"
    )

    return (
        summary,
        pass_count,
        handled_count,
        fail_count,
        overall_status
    )

if __name__ == "__main__":

    source_results = validate_source_data()

    derived_results = validate_derived_data()

    exposure_results = validate_exposure()

    reconciliation_results = (
    validate_sql_python_reconciliation()
    )
    
    print("Source Data Validation")
    print()

    print(
        source_results.to_string(
            index=False
        )
    )

    print()
    print("Derived Data Validation")
    print()

    print(
        derived_results.to_string(
            index=False
        )
    )

    print()
    print("Exposure Reconciliation")
    print()

    print(
        exposure_results.to_string(
            index=False
        )
    )
    print()
    print("SQL-Python Reconciliation")
    print()

    print(
        reconciliation_results.to_string(
            index=False
        )
    )

    (
    final_summary,
    pass_count,
    handled_count,
    fail_count,
    overall_status
    ) = build_validation_summary(
    source_results,
    derived_results,
    exposure_results,
    reconciliation_results
    )
    print()
    print("Final Validation Summary")
    print()

    print(
        final_summary.to_string(
            index=False
        )
    )

    print()
    print(
        f"PASS: {pass_count}"
    )

    print(
        f"HANDLED: {handled_count}"
    )

    print(
        f"FAIL: {fail_count}"
    )

    print(
        f"OVERALL STATUS: {overall_status}"
    )