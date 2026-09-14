from securities import (
    create_order,
    execute_order,
    create_settlement,
    settle_transaction,
    apply_settlement_to_portfolio,
    print_transaction_status,
    add_opening_cash,
    get_cash_balance,
    print_cash_balance,
    get_position,
    print_position
)


def main():
    add_opening_cash(
    currency="USD",
    amount=100000
    )

    print_cash_balance("USD")

    create_order(
        order_id="ORD001",
        symbol="SPY",
        side="BUY",
        quantity=10,
        order_price=600.0,
        currency="USD"
    )

    execute_order(
        execution_id="EXE001",
        order_id="ORD001",
        executed_price=598.5
    )

    create_settlement(
        settlement_id="STL001",
        execution_id="EXE001",
        settlement_date="2026-09-16"
    )

    print_transaction_status("ORD001")

    settle_transaction("STL001")

    print_transaction_status("ORD001")

    print()
    print("=== Portfolio Application ===")

    apply_settlement_to_portfolio("STL001")
    print_cash_balance("USD")
    print_position("SPY")

    print_transaction_status("ORD001")
    print()
    
    print("=== Idempotency Test ===")

    apply_settlement_to_portfolio("STL001")

    print()
    print("=== SELL Transaction Test ===")

    position_before_sell = get_position("SPY")
    cash_before_sell = get_cash_balance("USD")

    print(
        f"Before SELL | "
        f"SPY={position_before_sell}, "
        f"USD={cash_before_sell:.2f}"
    )

    create_order(
        order_id="ORD002",
        symbol="SPY",
        side="SELL",
        quantity=5,
        order_price=612.0,
        currency="USD"
    )

    execute_order(
        execution_id="EXE002",
        order_id="ORD002",
        executed_price=610.0
    )

    create_settlement(
        settlement_id="STL002",
        execution_id="EXE002",
        settlement_date="2026-09-17"
    )

    settle_transaction("STL002")

    apply_settlement_to_portfolio("STL002")

    position_after_sell = get_position("SPY")
    cash_after_sell = get_cash_balance("USD")

    print(
        f"After SELL  | "
        f"SPY={position_after_sell}, "
        f"USD={cash_after_sell:.2f}"
    )

    print_position("SPY")
    print_cash_balance("USD")

if __name__ == "__main__":
    main()