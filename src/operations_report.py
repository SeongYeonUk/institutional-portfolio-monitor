from securities import get_connection
from reconciliation import run_reconciliation


def get_count(conn, query, params=()):
    return conn.execute(
        query,
        params
    ).fetchone()[0]


def print_operations_report():
    with get_connection() as conn:

        total_orders = get_count(
            conn,
            """
            SELECT COUNT(*)
            FROM securities_orders
            """
        )

        ordered = get_count(
            conn,
            """
            SELECT COUNT(*)
            FROM securities_orders
            WHERE order_status = 'ORDERED'
            """
        )

        executed = get_count(
            conn,
            """
            SELECT COUNT(*)
            FROM securities_orders
            WHERE order_status = 'EXECUTED'
            """
        )

        total_executions = get_count(
            conn,
            """
            SELECT COUNT(*)
            FROM securities_executions
            """
        )

        total_settlements = get_count(
            conn,
            """
            SELECT COUNT(*)
            FROM securities_settlements
            """
        )

        pending = get_count(
            conn,
            """
            SELECT COUNT(*)
            FROM securities_settlements
            WHERE settlement_status = 'PENDING'
            """
        )

        settled = get_count(
            conn,
            """
            SELECT COUNT(*)
            FROM securities_settlements
            WHERE settlement_status = 'SETTLED'
            """
        )

        failed = get_count(
            conn,
            """
            SELECT COUNT(*)
            FROM securities_settlements
            WHERE settlement_status = 'FAILED'
            """
        )

        applied = get_count(
            conn,
            """
            SELECT COUNT(*)
            FROM securities_settlements
            WHERE portfolio_applied = 1
            """
        )

        not_applied = get_count(
            conn,
            """
            SELECT COUNT(*)
            FROM securities_settlements
            WHERE portfolio_applied = 0
            """
        )

        failure_rows = conn.execute(
            """
            SELECT
                failure_reason,
                COUNT(*) AS cnt

            FROM securities_settlements

            WHERE settlement_status = 'FAILED'

            GROUP BY failure_reason

            ORDER BY cnt DESC
            """
        ).fetchall()

        cash_rows = conn.execute(
            """
            SELECT
                currency,
                SUM(amount) AS balance

            FROM securities_cash_ledger

            GROUP BY currency

            ORDER BY currency
            """
        ).fetchall()

        pending_rows = conn.execute(
            """
            SELECT
                s.settlement_id,
                o.symbol,
                o.side,
                e.executed_quantity,
                s.settlement_amount,
                s.currency

            FROM securities_settlements s

            JOIN securities_executions e
              ON s.execution_id = e.execution_id

            JOIN securities_orders o
              ON e.order_id = o.order_id

            WHERE s.settlement_status = 'PENDING'

            ORDER BY s.settlement_date
            """
        ).fetchall()

        failed_rows = conn.execute(
            """
            SELECT
                s.settlement_id,
                o.symbol,
                o.side,
                s.settlement_amount,
                s.currency,
                s.failure_reason

            FROM securities_settlements s

            JOIN securities_executions e
              ON s.execution_id = e.execution_id

            JOIN securities_orders o
              ON e.order_id = o.order_id

            WHERE s.settlement_status = 'FAILED'

            ORDER BY s.settlement_id
            """
        ).fetchall()

    print()
    print("========================================")
    print("Securities Operations Monitoring Report")
    print("========================================")

    print()
    print("[Order / Execution]")
    print(f"Total Orders       : {total_orders}")
    print(f"ORDERED            : {ordered}")
    print(f"EXECUTED           : {executed}")
    print(f"Total Executions   : {total_executions}")

    print()
    print("[Settlement]")
    print(f"Total Settlements  : {total_settlements}")
    print(f"PENDING            : {pending}")
    print(f"SETTLED            : {settled}")
    print(f"FAILED             : {failed}")

    print()
    print("[Portfolio Application]")
    print(f"Applied            : {applied}")
    print(f"Not Applied        : {not_applied}")

    print()
    print("[Cash Balance]")

    if cash_rows:
        for row in cash_rows:
            print(
                f"{row['currency']:5s}: "
                f"{row['balance']:.2f}"
            )
    else:
        print("No cash ledger data")

    print()
    print("[Failure Summary]")

    if failure_rows:
        for row in failure_rows:
            print(
                f"{row['failure_reason']:25s}: "
                f"{row['cnt']}"
            )
    else:
        print("No settlement failures")

    print()
    print("[Pending Settlements]")

    if pending_rows:
        for row in pending_rows:
            print(
                f"{row['settlement_id']} | "
                f"{row['side']} "
                f"{row['symbol']} "
                f"{row['executed_quantity']} | "
                f"{row['settlement_amount']:.2f} "
                f"{row['currency']}"
            )
    else:
        print("None")

    print()
    print("[Failed Settlements]")

    if failed_rows:
        for row in failed_rows:
            print(
                f"{row['settlement_id']} | "
                f"{row['side']} "
                f"{row['symbol']} | "
                f"{row['settlement_amount']:.2f} "
                f"{row['currency']} | "
                f"{row['failure_reason']}"
            )
    else:
        print("None")

    print()
    print("========================================")
    print("Reconciliation")
    print("========================================")

    reconciliation_pass = run_reconciliation()

    print()
    print("========================================")

    if failed > 0:
        print(
            "OPERATIONS STATUS: ATTENTION "
            f"({failed} failed settlement(s))"
        )

    elif pending > 0:
        print(
            "OPERATIONS STATUS: PENDING "
            f"({pending} settlement(s))"
        )

    elif not reconciliation_pass:
        print(
            "OPERATIONS STATUS: "
            "RECONCILIATION ERROR"
        )

    else:
        print(
            "OPERATIONS STATUS: NORMAL"
        )

    print("========================================")


if __name__ == "__main__":
    print_operations_report()