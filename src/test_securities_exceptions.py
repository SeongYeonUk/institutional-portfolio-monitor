from init_db import init_db

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


def expect_error(name, func):
    try:
        func()

    except ValueError as e:
        print(
            f"[PASS] {name}"
        )
        print(
            f"       {e}"
        )

    else:
        print(
            f"[FAIL] {name} - error was expected"
        )


def main():

    # 항상 깨끗한 DB에서 예외 테스트 시작
    init_db()

    add_opening_cash(
        currency="USD",
        amount=100000
    )

    print()
    print("================================")
    print("1. PENDING Settlement Test")
    print("================================")

    create_order(
        order_id="ORD_PENDING",
        symbol="SPY",
        side="BUY",
        quantity=1,
        order_price=500,
        currency="USD"
    )

    execute_order(
        execution_id="EXE_PENDING",
        order_id="ORD_PENDING",
        executed_price=500
    )

    create_settlement(
        settlement_id="STL_PENDING",
        execution_id="EXE_PENDING",
        settlement_date="2026-09-16"
    )

    expect_error(
        "PENDING settlement cannot be applied",
        lambda: apply_settlement_to_portfolio(
            "STL_PENDING"
        )
    )

    print_transaction_status(
        "ORD_PENDING"
    )


    print()
    print("================================")
    print("2. Insufficient Cash Test")
    print("================================")

    create_order(
        order_id="ORD_CASH_FAIL",
        symbol="SPY",
        side="BUY",
        quantity=1000,
        order_price=1000,
        currency="USD"
    )

    execute_order(
        execution_id="EXE_CASH_FAIL",
        order_id="ORD_CASH_FAIL",
        executed_price=1000
    )

    create_settlement(
        settlement_id="STL_CASH_FAIL",
        execution_id="EXE_CASH_FAIL",
        settlement_date="2026-09-16"
    )

    settle_transaction(
        "STL_CASH_FAIL"
    )

    print_transaction_status(
        "ORD_CASH_FAIL"
    )

    expect_error(
        "FAILED settlement cannot be applied",
        lambda: apply_settlement_to_portfolio(
            "STL_CASH_FAIL"
        )
    )


    print()
    print("================================")
    print("3. Insufficient Position Test")
    print("================================")

    position = get_position("SPY")

    print(
        f"Current SPY position: {position}"
    )

    create_order(
        order_id="ORD_POSITION_FAIL",
        symbol="SPY",
        side="SELL",
        quantity=99999,
        order_price=600,
        currency="USD"
    )

    execute_order(
        execution_id="EXE_POSITION_FAIL",
        order_id="ORD_POSITION_FAIL",
        executed_price=600
    )

    create_settlement(
        settlement_id="STL_POSITION_FAIL",
        execution_id="EXE_POSITION_FAIL",
        settlement_date="2026-09-16"
    )

    settle_transaction(
        "STL_POSITION_FAIL"
    )

    print_transaction_status(
        "ORD_POSITION_FAIL"
    )

    expect_error(
        "Insufficient position settlement "
        "cannot be applied",
        lambda: apply_settlement_to_portfolio(
            "STL_POSITION_FAIL"
        )
    )


    print()
    print("================================")
    print("4. Ledger Integrity Check")
    print("================================")

    print_position("SPY")
    print_cash_balance("USD")

    print(
        "Expected:"
    )
    print(
        "SPY position unchanged from original"
    )
    print(
        "USD cash = 100000.00"
    )


    print()
    print("================================")
    print("5. Normal Transaction After Failures")
    print("================================")

    create_order(
        order_id="ORD_OK",
        symbol="SPY",
        side="BUY",
        quantity=2,
        order_price=500,
        currency="USD"
    )

    execute_order(
        execution_id="EXE_OK",
        order_id="ORD_OK",
        executed_price=500
    )

    create_settlement(
        settlement_id="STL_OK",
        execution_id="EXE_OK",
        settlement_date="2026-09-16"
    )

    settle_transaction(
        "STL_OK"
    )

    apply_settlement_to_portfolio(
        "STL_OK"
    )

    print_position("SPY")
    print_cash_balance("USD")


if __name__ == "__main__":
    main()