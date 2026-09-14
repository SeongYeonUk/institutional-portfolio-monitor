PRAGMA foreign_keys = ON;

-- =========================================================
-- 1. Orders
-- 투자자의 주문 정보를 관리한다.
-- =========================================================
CREATE TABLE IF NOT EXISTS securities_orders (
    order_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,

    side TEXT NOT NULL
        CHECK (side IN ('BUY', 'SELL')),

    order_quantity INTEGER NOT NULL
        CHECK (order_quantity > 0),

    order_price REAL NOT NULL
        CHECK (order_price > 0),

    currency TEXT NOT NULL,

    order_status TEXT NOT NULL
        CHECK (
            order_status IN (
                'ORDERED',
                'EXECUTED',
                'CANCELLED'
            )
        ),

    ordered_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- =========================================================
-- 2. Executions
-- 주문이 시장에서 체결된 결과를 관리한다.
-- 1차에서는 한 주문당 하나의 체결만 처리한다.
-- 부분체결은 추후 증권사형 2차 확장에서 추가한다.
-- =========================================================
CREATE TABLE IF NOT EXISTS securities_executions (
    execution_id TEXT PRIMARY KEY,

    order_id TEXT NOT NULL UNIQUE,

    executed_quantity INTEGER NOT NULL
        CHECK (executed_quantity > 0),

    executed_price REAL NOT NULL
        CHECK (executed_price > 0),

    executed_at TEXT NOT NULL,

    FOREIGN KEY (order_id)
        REFERENCES securities_orders(order_id)
);


-- =========================================================
-- 3. Settlements
-- 체결 이후 실제 결제 처리 상태를 관리한다.
-- =========================================================
CREATE TABLE IF NOT EXISTS securities_settlements (
    settlement_id TEXT PRIMARY KEY,

    execution_id TEXT NOT NULL UNIQUE,

    settlement_date TEXT NOT NULL,

    settlement_amount REAL NOT NULL,

    currency TEXT NOT NULL,

    settlement_status TEXT NOT NULL
        CHECK (
            settlement_status IN (
                'PENDING',
                'SETTLED',
                'FAILED'
            )
        ),

    failure_reason TEXT,

    settled_at TEXT,

    -- 기존 portfolio trade 원장에 반영됐는지 여부
    portfolio_applied INTEGER NOT NULL DEFAULT 0
        CHECK (portfolio_applied IN (0, 1)),

    -- 실제 생성된 trade ID
    applied_trade_id TEXT UNIQUE,

    applied_at TEXT,

    FOREIGN KEY (execution_id)
        REFERENCES securities_executions(execution_id),


    CHECK (
        (portfolio_applied = 0 AND applied_trade_id IS NULL)
        OR
        (portfolio_applied = 1 AND applied_trade_id IS NOT NULL)
    )
);

-- =========================================================
-- 4. Cash Ledger
-- 증권 거래에 따른 통화별 현금 변동을 기록한다.
-- 잔액은 ledger 합계로 계산한다.
-- =========================================================
CREATE TABLE IF NOT EXISTS securities_cash_ledger (
    cash_entry_id TEXT PRIMARY KEY,

    settlement_id TEXT UNIQUE,

    currency TEXT NOT NULL,

    amount REAL NOT NULL,

    entry_type TEXT NOT NULL
        CHECK (
            entry_type IN (
                'OPENING',
                'BUY',
                'SELL'
            )
        ),

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (settlement_id)
        REFERENCES securities_settlements(settlement_id)
);