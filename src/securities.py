from pathlib import Path
import sqlite3
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "portfolio.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def create_order(
    order_id,
    symbol,
    side,
    quantity,
    order_price,
    currency
):
    side = side.upper()

    if side not in ("BUY", "SELL"):
        raise ValueError("side must be BUY or SELL")

    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    if order_price <= 0:
        raise ValueError("order_price must be greater than 0")

    with get_connection() as conn:

        # 기존 포트폴리오의 asset인지 확인
        asset = conn.execute(
            """
            SELECT symbol
            FROM asset
            WHERE symbol = ?
            """,
            (symbol,)
        ).fetchone()

        if asset is None:
            raise ValueError(
                f"Unknown asset symbol: {symbol}"
            )

        conn.execute(
            """
            INSERT INTO securities_orders (
                order_id,
                symbol,
                side,
                order_quantity,
                order_price,
                currency,
                order_status,
                ordered_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'ORDERED', ?)
            """,
            (
                order_id,
                symbol,
                side,
                quantity,
                order_price,
                currency,
                now()
            )
        )

        print(
            f"[ORDER CREATED] "
            f"{order_id} | {side} {symbol} "
            f"{quantity} @ {order_price} {currency}"
        )


def execute_order(
    execution_id,
    order_id,
    executed_price
):
    with get_connection() as conn:

        order = conn.execute(
            """
            SELECT *
            FROM securities_orders
            WHERE order_id = ?
            """,
            (order_id,)
        ).fetchone()

        if order is None:
            raise ValueError(
                f"Order not found: {order_id}"
            )

        if order["order_status"] != "ORDERED":
            raise ValueError(
                f"Order cannot be executed "
                f"from status {order['order_status']}"
            )

        quantity = order["order_quantity"]

        conn.execute(
            """
            INSERT INTO securities_executions (
                execution_id,
                order_id,
                executed_quantity,
                executed_price,
                executed_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                execution_id,
                order_id,
                quantity,
                executed_price,
                now()
            )
        )

        conn.execute(
            """
            UPDATE securities_orders
            SET order_status = 'EXECUTED'
            WHERE order_id = ?
            """,
            (order_id,)
        )

        print(
            f"[ORDER EXECUTED] "
            f"{order_id} -> {execution_id} | "
            f"{quantity} @ {executed_price}"
        )


def create_settlement(
    settlement_id,
    execution_id,
    settlement_date
):
    with get_connection() as conn:

        row = conn.execute(
            """
            SELECT
                e.execution_id,
                e.executed_quantity,
                e.executed_price,
                o.currency
            FROM securities_executions e
            JOIN securities_orders o
              ON e.order_id = o.order_id
            WHERE e.execution_id = ?
            """,
            (execution_id,)
        ).fetchone()

        if row is None:
            raise ValueError(
                f"Execution not found: {execution_id}"
            )

        settlement_amount = (
            row["executed_quantity"]
            * row["executed_price"]
        )

        conn.execute(
            """
            INSERT INTO securities_settlements (
                settlement_id,
                execution_id,
                settlement_date,
                settlement_amount,
                currency,
                settlement_status
            )
            VALUES (?, ?, ?, ?, ?, 'PENDING')
            """,
            (
                settlement_id,
                execution_id,
                settlement_date,
                settlement_amount,
                row["currency"]
            )
        )

        print(
            f"[SETTLEMENT CREATED] "
            f"{settlement_id} | "
            f"{settlement_amount:.2f} "
            f"{row['currency']} | PENDING"
        )


def settle_transaction(settlement_id):
    with get_connection() as conn:

        settlement = conn.execute(
            """
            SELECT
                s.settlement_id,
                s.settlement_status,
                s.settlement_amount,
                s.currency,

                e.executed_quantity,

                o.symbol,
                o.side,

                a.asset_id

            FROM securities_settlements s

            JOIN securities_executions e
              ON s.execution_id = e.execution_id

            JOIN securities_orders o
              ON e.order_id = o.order_id

            JOIN asset a
              ON o.symbol = a.symbol

            WHERE s.settlement_id = ?
            """,
            (settlement_id,)
        ).fetchone()

        if settlement is None:
            raise ValueError(
                f"Settlement not found: {settlement_id}"
            )

        if settlement["settlement_status"] != "PENDING":
            raise ValueError(
                f"Settlement cannot be completed "
                f"from status "
                f"{settlement['settlement_status']}"
            )

        # ----------------------------------------
        # BUY: 결제에 필요한 현금 확인
        # ----------------------------------------
        if settlement["side"] == "BUY":

            current_cash = conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM securities_cash_ledger
                WHERE currency = ?
                """,
                (settlement["currency"],)
            ).fetchone()[0]

            if current_cash < settlement["settlement_amount"]:

                conn.execute(
                    """
                    UPDATE securities_settlements
                    SET
                        settlement_status = 'FAILED',
                        failure_reason = 'INSUFFICIENT_CASH'
                    WHERE settlement_id = ?
                    """,
                    (settlement_id,)
                )

                print(
                    f"[SETTLEMENT FAILED] "
                    f"{settlement_id} | "
                    f"INSUFFICIENT_CASH | "
                    f"balance={current_cash:.2f}, "
                    f"required="
                    f"{settlement['settlement_amount']:.2f}"
                )

                return False

        # ----------------------------------------
        # SELL: 결제할 수량 보유 여부 확인
        # ----------------------------------------
        if settlement["side"] == "SELL":

            current_position = conn.execute(
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
                (settlement["asset_id"],)
            ).fetchone()[0]

            if current_position < settlement["executed_quantity"]:

                conn.execute(
                    """
                    UPDATE securities_settlements
                    SET
                        settlement_status = 'FAILED',
                        failure_reason = 'INSUFFICIENT_POSITION'
                    WHERE settlement_id = ?
                    """,
                    (settlement_id,)
                )

                print(
                    f"[SETTLEMENT FAILED] "
                    f"{settlement_id} | "
                    f"INSUFFICIENT_POSITION | "
                    f"position={current_position}, "
                    f"required="
                    f"{settlement['executed_quantity']}"
                )

                return False

        # ----------------------------------------
        # 정상 결제
        # ----------------------------------------

        conn.execute(
            """
            UPDATE securities_settlements
            SET
                settlement_status = 'SETTLED',
                failure_reason = NULL,
                settled_at = ?
            WHERE settlement_id = ?
            """,
            (
                now(),
                settlement_id
            )
        )

        print(
            f"[SETTLED] {settlement_id}"
        )

        return True


def print_transaction_status(order_id):
    with get_connection() as conn:

        row = conn.execute(
            """
            SELECT
                o.order_id,
                o.symbol,
                o.side,
                o.order_quantity,
                o.order_status,

                e.execution_id,
                e.executed_quantity,
                e.executed_price,

                s.settlement_id,
                s.settlement_amount,
                s.currency,
                s.settlement_status,
                s.portfolio_applied,
                s.applied_trade_id

            FROM securities_orders o

            LEFT JOIN securities_executions e
              ON o.order_id = e.order_id

            LEFT JOIN securities_settlements s
              ON e.execution_id = s.execution_id

            WHERE o.order_id = ?
            """,
            (order_id,)
        ).fetchone()

        if row is None:
            print("Transaction not found.")
            return

        print()
        print("=== Securities Transaction ===")
        print(f"Order ID          : {row['order_id']}")
        print(f"Asset             : {row['symbol']}")
        print(f"Side              : {row['side']}")
        print(f"Quantity          : {row['order_quantity']}")
        print(f"Order Status      : {row['order_status']}")
        print(f"Execution ID      : {row['execution_id']}")
        print(f"Executed Price    : {row['executed_price']}")
        print(f"Settlement ID     : {row['settlement_id']}")
        print(f"Settlement Amount : {row['settlement_amount']}")
        print(f"Currency          : {row['currency']}")
        print(f"Settlement Status : {row['settlement_status']}")
        print(f"Portfolio Applied : {row['portfolio_applied']}")
        print(f"Applied Trade ID  : {row['applied_trade_id']}")

        if row is None:
            print("Transaction not found.")
            return

        print()
        print("=== Securities Transaction ===")
        print(f"Order ID          : {row['order_id']}")
        print(f"Asset             : {row['symbol']}")
        print(f"Side              : {row['side']}")
        print(f"Quantity          : {row['order_quantity']}")
        print(f"Order Status      : {row['order_status']}")
        print(f"Execution ID      : {row['execution_id']}")
        print(f"Executed Price    : {row['executed_price']}")
        print(f"Settlement ID     : {row['settlement_id']}")
        print(f"Settlement Amount : {row['settlement_amount']}")
        print(f"Currency          : {row['currency']}")
        print(f"Settlement Status : {row['settlement_status']}")
        print(f"Portfolio Applied : {row['portfolio_applied']}")
        print(f"Applied Trade ID  : {row['applied_trade_id']}")

def apply_settlement_to_portfolio(settlement_id):
    with get_connection() as conn:

        conn.execute("BEGIN IMMEDIATE")

        row = conn.execute(
            """
            SELECT
                s.settlement_id,
                s.settlement_date,
                s.settlement_amount,
                s.currency,
                s.settlement_status,
                s.portfolio_applied,
                s.applied_trade_id,

                e.executed_quantity,
                e.executed_price,

                o.symbol,
                o.side,

                a.asset_id

            FROM securities_settlements s

            JOIN securities_executions e
              ON s.execution_id = e.execution_id

            JOIN securities_orders o
              ON e.order_id = o.order_id

            JOIN asset a
              ON o.symbol = a.symbol

            WHERE s.settlement_id = ?
            """,
            (settlement_id,)
        ).fetchone()

        if row is None:
            raise ValueError(
                f"Settlement not found: {settlement_id}"
            )

        if row["settlement_status"] != "SETTLED":
            raise ValueError(
                f"Settlement must be SETTLED before "
                f"portfolio application: "
                f"{row['settlement_status']}"
            )

        # 이미 포트폴리오 반영된 결제는 재처리하지 않음
        if row["portfolio_applied"] == 1:
            print(
                f"[PORTFOLIO SKIPPED] "
                f"{settlement_id} already applied "
                f"as {row['applied_trade_id']}"
            )

            return row["applied_trade_id"]

        quantity = row["executed_quantity"]
        settlement_amount = row["settlement_amount"]

        # -------------------------------------------------
        # BUY: 현금 충분 여부 확인
        # -------------------------------------------------
        if row["side"] == "BUY":

            current_cash = conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM securities_cash_ledger
                WHERE currency = ?
                """,
                (row["currency"],)
            ).fetchone()[0]

            if current_cash < settlement_amount:
                raise ValueError(
                    f"Insufficient cash: "
                    f"{row['currency']} "
                    f"balance={current_cash:.2f}, "
                    f"required={settlement_amount:.2f}"
                )

        # -------------------------------------------------
        # SELL: 현재 보유수량 확인
        # -------------------------------------------------
        if row["side"] == "SELL":

            current_position = conn.execute(
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
                (row["asset_id"],)
            ).fetchone()[0]

            if current_position < quantity:
                raise ValueError(
                    f"Insufficient position for "
                    f"{row['symbol']}: "
                    f"current={current_position}, "
                    f"sell={quantity}"
                )

        # -------------------------------------------------
        # Portfolio trade 원장 반영
        # -------------------------------------------------

        trade_id = f"SEC_{settlement_id}"

        conn.execute(
            """
            INSERT INTO trade (
                trade_id,
                trade_date,
                asset_id,
                trade_type,
                quantity,
                trade_price
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                trade_id,
                row["settlement_date"],
                row["asset_id"],
                row["side"],
                quantity,
                row["executed_price"]
            )
        )

        # -------------------------------------------------
        # Cash 원장 반영
        # BUY  -> 현금 감소
        # SELL -> 현금 증가
        # -------------------------------------------------

        if row["side"] == "BUY":
            cash_amount = -settlement_amount

        else:
            cash_amount = settlement_amount

        cash_entry_id = f"CASH_{settlement_id}"

        conn.execute(
            """
            INSERT INTO securities_cash_ledger (
                cash_entry_id,
                settlement_id,
                currency,
                amount,
                entry_type
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                cash_entry_id,
                settlement_id,
                row["currency"],
                cash_amount,
                row["side"]
            )
        )

        # -------------------------------------------------
        # Settlement 포트폴리오 반영 완료
        # -------------------------------------------------

        conn.execute(
            """
            UPDATE securities_settlements
            SET
                portfolio_applied = 1,
                applied_trade_id = ?,
                applied_at = ?
            WHERE settlement_id = ?
            """,
            (
                trade_id,
                now(),
                settlement_id
            )
        )

        print(
            f"[PORTFOLIO APPLIED] "
            f"{settlement_id} -> {trade_id} | "
            f"{row['side']} {row['symbol']} "
            f"{quantity} @ {row['executed_price']}"
        )

        print(
            f"[CASH APPLIED] "
            f"{cash_entry_id} | "
            f"{row['currency']} "
            f"{cash_amount:.2f}"
        )

        return trade_id
    
def get_cash_balance(currency):
    with get_connection() as conn:

        balance = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM securities_cash_ledger
            WHERE currency = ?
            """,
            (currency,)
        ).fetchone()[0]

        return balance


def add_opening_cash(currency, amount):
    if amount <= 0:
        raise ValueError(
            "Opening cash must be greater than 0"
        )

    cash_entry_id = f"OPENING_{currency}"

    with get_connection() as conn:

        existing = conn.execute(
            """
            SELECT cash_entry_id
            FROM securities_cash_ledger
            WHERE cash_entry_id = ?
            """,
            (cash_entry_id,)
        ).fetchone()

        if existing is not None:
            print(
                f"[OPENING CASH SKIPPED] "
                f"{currency} already exists"
            )
            return

        conn.execute(
            """
            INSERT INTO securities_cash_ledger (
                cash_entry_id,
                settlement_id,
                currency,
                amount,
                entry_type
            )
            VALUES (?, NULL, ?, ?, 'OPENING')
            """,
            (
                cash_entry_id,
                currency,
                amount
            )
        )

        print(
            f"[OPENING CASH] "
            f"{currency} {amount:.2f}"
        )


def print_cash_balance(currency):
    balance = get_cash_balance(currency)

    print(
        f"[CASH BALANCE] "
        f"{currency} {balance:.2f}"
    )


def get_position(symbol):
    with get_connection() as conn:

        row = conn.execute(
            """
            SELECT
                a.asset_id,
                COALESCE(
                    SUM(
                        CASE
                            WHEN t.trade_type = 'BUY'
                                THEN t.quantity
                            WHEN t.trade_type = 'SELL'
                                THEN -t.quantity
                            ELSE 0
                        END
                    ),
                    0
                ) AS position

            FROM asset a

            LEFT JOIN trade t
              ON a.asset_id = t.asset_id

            WHERE a.symbol = ?

            GROUP BY a.asset_id
            """,
            (symbol,)
        ).fetchone()

        if row is None:
            raise ValueError(
                f"Unknown asset symbol: {symbol}"
            )

        return row["position"]


def print_position(symbol):
    position = get_position(symbol)

    print(
        f"[POSITION] "
        f"{symbol} {position}"
    )