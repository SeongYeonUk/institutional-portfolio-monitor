from securities import get_connection


FLOAT_TOLERANCE = 1e-6


def almost_equal(a, b):
    return abs(a - b) <= FLOAT_TOLERANCE


def reconcile_trade_details():
    """
    증권 결제 데이터와 실제 portfolio trade 원장을
    거래 단위로 비교한다.
    """

    with get_connection() as conn:

        rows = conn.execute(
            """
            SELECT
                s.settlement_id,
                s.applied_trade_id,
                s.settlement_date,

                o.side,
                o.symbol,

                e.executed_quantity,
                e.executed_price,

                a.asset_id,

                t.trade_id,
                t.trade_date,
                t.asset_id AS actual_asset_id,
                t.trade_type,
                t.quantity AS actual_quantity,
                t.trade_price AS actual_price

            FROM securities_settlements s

            JOIN securities_executions e
              ON s.execution_id = e.execution_id

            JOIN securities_orders o
              ON e.order_id = o.order_id

            JOIN asset a
              ON o.symbol = a.symbol

            LEFT JOIN trade t
              ON s.applied_trade_id = t.trade_id

            WHERE s.portfolio_applied = 1

            ORDER BY s.settlement_id
            """
        ).fetchall()

        failures = []

        for row in rows:

            errors = []

            if row["trade_id"] is None:
                errors.append("TRADE_NOT_FOUND")

            else:
                if row["settlement_date"] != row["trade_date"]:
                    errors.append("TRADE_DATE_MISMATCH")

                if row["asset_id"] != row["actual_asset_id"]:
                    errors.append("ASSET_MISMATCH")

                if row["side"] != row["trade_type"]:
                    errors.append("SIDE_MISMATCH")

                if row["executed_quantity"] != row["actual_quantity"]:
                    errors.append("QUANTITY_MISMATCH")

                if not almost_equal(
                    row["executed_price"],
                    row["actual_price"]
                ):
                    errors.append("PRICE_MISMATCH")

            if errors:
                failures.append(
                    (
                        row["settlement_id"],
                        errors
                    )
                )

        return len(rows), failures


def reconcile_cash_details():
    """
    결제정보에서 예상되는 현금변동과
    securities_cash_ledger를 거래 단위로 비교한다.
    """

    with get_connection() as conn:

        rows = conn.execute(
            """
            SELECT
                s.settlement_id,
                s.settlement_amount,
                s.currency,

                o.side,

                c.cash_entry_id,
                c.currency AS actual_currency,
                c.amount AS actual_amount,
                c.entry_type

            FROM securities_settlements s

            JOIN securities_executions e
              ON s.execution_id = e.execution_id

            JOIN securities_orders o
              ON e.order_id = o.order_id

            LEFT JOIN securities_cash_ledger c
              ON s.settlement_id = c.settlement_id

            WHERE s.portfolio_applied = 1

            ORDER BY s.settlement_id
            """
        ).fetchall()

        failures = []

        for row in rows:

            errors = []

            expected_amount = (
                -row["settlement_amount"]
                if row["side"] == "BUY"
                else row["settlement_amount"]
            )

            if row["cash_entry_id"] is None:
                errors.append("CASH_ENTRY_NOT_FOUND")

            else:
                if row["currency"] != row["actual_currency"]:
                    errors.append("CURRENCY_MISMATCH")

                if row["side"] != row["entry_type"]:
                    errors.append("ENTRY_TYPE_MISMATCH")

                if not almost_equal(
                    expected_amount,
                    row["actual_amount"]
                ):
                    errors.append("CASH_AMOUNT_MISMATCH")

            if errors:
                failures.append(
                    (
                        row["settlement_id"],
                        errors
                    )
                )

        return len(rows), failures


def reconcile_positions():
    """
    기존 legacy trade + 증권결제 기대수량을 계산한 값과
    실제 전체 trade 원장의 포지션을 비교한다.
    """

    with get_connection() as conn:

        symbols = conn.execute(
            """
            SELECT symbol, asset_id
            FROM asset
            ORDER BY symbol
            """
        ).fetchall()

        failures = []
        results = []

        for asset in symbols:

            asset_id = asset["asset_id"]
            symbol = asset["symbol"]

            # 기존 프로젝트 거래만 이용한 기본 포지션
            legacy_position = conn.execute(
                """
                SELECT COALESCE(
                    SUM(
                        CASE
                            WHEN trade_type = 'BUY'
                                THEN quantity
                            WHEN trade_type = 'SELL'
                                THEN -quantity
                            ELSE 0
                        END
                    ),
                    0
                )
                FROM trade
                WHERE asset_id = ?
                  AND trade_id NOT LIKE 'SEC_%'
                """,
                (asset_id,)
            ).fetchone()[0]

            # 증권 시스템에서 기대되는 추가 포지션
            securities_delta = conn.execute(
                """
                SELECT COALESCE(
                    SUM(
                        CASE
                            WHEN o.side = 'BUY'
                                THEN e.executed_quantity
                            WHEN o.side = 'SELL'
                                THEN -e.executed_quantity
                            ELSE 0
                        END
                    ),
                    0
                )

                FROM securities_settlements s

                JOIN securities_executions e
                  ON s.execution_id = e.execution_id

                JOIN securities_orders o
                  ON e.order_id = o.order_id

                WHERE s.portfolio_applied = 1
                  AND o.symbol = ?
                """,
                (symbol,)
            ).fetchone()[0]

            expected = legacy_position + securities_delta

            # 실제 전체 trade 원장 포지션
            actual = conn.execute(
                """
                SELECT COALESCE(
                    SUM(
                        CASE
                            WHEN trade_type = 'BUY'
                                THEN quantity
                            WHEN trade_type = 'SELL'
                                THEN -quantity
                            ELSE 0
                        END
                    ),
                    0
                )
                FROM trade
                WHERE asset_id = ?
                """,
                (asset_id,)
            ).fetchone()[0]

            results.append(
                (
                    symbol,
                    expected,
                    actual
                )
            )

            if expected != actual:
                failures.append(
                    (
                        symbol,
                        expected,
                        actual
                    )
                )

        return results, failures


def reconcile_cash_balances():
    """
    Opening Cash + 결제 기대 현금흐름과
    실제 cash ledger 합계를 통화별로 비교한다.
    """

    with get_connection() as conn:

        currencies = conn.execute(
            """
            SELECT DISTINCT currency
            FROM securities_cash_ledger
            ORDER BY currency
            """
        ).fetchall()

        results = []
        failures = []

        for row in currencies:

            currency = row["currency"]

            opening_cash = conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM securities_cash_ledger
                WHERE currency = ?
                  AND entry_type = 'OPENING'
                """,
                (currency,)
            ).fetchone()[0]

            expected_flow = conn.execute(
                """
                SELECT COALESCE(
                    SUM(
                        CASE
                            WHEN o.side = 'BUY'
                                THEN -s.settlement_amount
                            WHEN o.side = 'SELL'
                                THEN s.settlement_amount
                            ELSE 0
                        END
                    ),
                    0
                )

                FROM securities_settlements s

                JOIN securities_executions e
                  ON s.execution_id = e.execution_id

                JOIN securities_orders o
                  ON e.order_id = o.order_id

                WHERE s.portfolio_applied = 1
                  AND s.currency = ?
                """,
                (currency,)
            ).fetchone()[0]

            expected = opening_cash + expected_flow

            actual = conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM securities_cash_ledger
                WHERE currency = ?
                """,
                (currency,)
            ).fetchone()[0]

            results.append(
                (
                    currency,
                    expected,
                    actual
                )
            )

            if not almost_equal(
                expected,
                actual
            ):
                failures.append(
                    (
                        currency,
                        expected,
                        actual
                    )
                )

        return results, failures


def run_reconciliation():

    print()
    print("================================")
    print("Securities Reconciliation")
    print("================================")

    trade_count, trade_failures = (
        reconcile_trade_details()
    )

    cash_count, cash_failures = (
        reconcile_cash_details()
    )

    position_results, position_failures = (
        reconcile_positions()
    )

    cash_results, cash_balance_failures = (
        reconcile_cash_balances()
    )

    print()
    print("[1] Trade Detail Reconciliation")

    if trade_failures:
        print("FAIL")

        for settlement_id, errors in trade_failures:
            print(
                f"  {settlement_id}: "
                f"{', '.join(errors)}"
            )

    else:
        print(
            f"PASS ({trade_count} transactions)"
        )

    print()
    print("[2] Cash Detail Reconciliation")

    if cash_failures:
        print("FAIL")

        for settlement_id, errors in cash_failures:
            print(
                f"  {settlement_id}: "
                f"{', '.join(errors)}"
            )

    else:
        print(
            f"PASS ({cash_count} transactions)"
        )

    print()
    print("[3] Position Reconciliation")

    for symbol, expected, actual in position_results:
        print(
            f"{symbol:10s} "
            f"expected={expected:<8} "
            f"actual={actual:<8}"
        )

    if position_failures:
        print("Result: FAIL")
    else:
        print("Result: PASS")

    print()
    print("[4] Cash Balance Reconciliation")

    for currency, expected, actual in cash_results:
        print(
            f"{currency:5s} "
            f"expected={expected:.2f} "
            f"actual={actual:.2f}"
        )

    if cash_balance_failures:
        print("Result: FAIL")
    else:
        print("Result: PASS")

    overall_pass = not (
        trade_failures
        or cash_failures
        or position_failures
        or cash_balance_failures
    )

    print()
    print("================================")

    if overall_pass:
        print("OVERALL RECONCILIATION: PASS")
    else:
        print("OVERALL RECONCILIATION: FAIL")

    print("================================")

    return overall_pass


if __name__ == "__main__":
    run_reconciliation()