from pathlib import Path
import sqlite3

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "db" / "portfolio.db"

OUTPUT_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "portfolio_history.csv"
)


def load_data():
    with sqlite3.connect(DB_PATH) as conn:

        assets = pd.read_sql_query(
            """
            SELECT *
            FROM asset
            ORDER BY asset_id
            """,
            conn
        )

        trades = pd.read_sql_query(
            """
            SELECT *
            FROM trade
            ORDER BY trade_date, trade_id
            """,
            conn
        )

        prices = pd.read_sql_query(
            """
            SELECT *
            FROM price
            ORDER BY price_date, asset_id
            """,
            conn
        )

        fx = pd.read_sql_query(
            """
            SELECT *
            FROM fx_rate
            ORDER BY fx_date, currency
            """,
            conn
        )

    trades["trade_date"] = pd.to_datetime(
        trades["trade_date"]
    )

    prices["price_date"] = pd.to_datetime(
        prices["price_date"]
    )

    fx["fx_date"] = pd.to_datetime(
        fx["fx_date"]
    )

    return assets, trades, prices, fx


def build_daily_positions(
    assets,
    trades,
    dates
):
    signed_trades = trades.copy()

    signed_trades["signed_quantity"] = (
        signed_trades["quantity"].where(
            signed_trades["trade_type"] == "BUY",
            -signed_trades["quantity"]
        )
    )

    daily_trade = (
        signed_trades
        .groupby(
            ["trade_date", "asset_id"]
        )["signed_quantity"]
        .sum()
        .unstack(fill_value=0)
    )

    daily_trade = daily_trade.reindex(
        dates,
        fill_value=0
    )

    positions = daily_trade.cumsum()

    for asset_id in assets["asset_id"]:
        if asset_id not in positions.columns:
            positions[asset_id] = 0

    positions = positions[
        assets["asset_id"].tolist()
    ]

    return positions


def build_price_matrix(
    assets,
    prices,
    dates
):
    price_matrix = prices.pivot(
        index="price_date",
        columns="asset_id",
        values="close_price"
    )

    price_matrix = price_matrix.reindex(
        dates
    )

    # 평가일 이전의 가장 최근 유효가격 사용
    price_matrix = price_matrix.ffill()

    for asset_id in assets["asset_id"]:
        if asset_id not in price_matrix.columns:
            price_matrix[asset_id] = pd.NA

    return price_matrix[
        assets["asset_id"].tolist()
    ]


def build_fx_matrix(
    assets,
    fx,
    dates
):
    fx_matrix = fx.pivot(
        index="fx_date",
        columns="currency",
        values="rate_to_krw"
    )

    fx_matrix = fx_matrix.reindex(
        dates
    )

    fx_matrix = fx_matrix.ffill()

    result = pd.DataFrame(
        index=dates
    )

    for _, asset in assets.iterrows():
        asset_id = asset["asset_id"]
        currency = asset["currency"]

        result[asset_id] = (
            fx_matrix[currency]
        )

    return result


def build_daily_trade_flows(
    assets,
    trades,
    fx,
    dates
):
    asset_currency = (
        assets
        .set_index("asset_id")["currency"]
        .to_dict()
    )

    fx_matrix = (
        fx.pivot(
            index="fx_date",
            columns="currency",
            values="rate_to_krw"
        )
        .reindex(dates)
        .ffill()
    )

    flows = pd.Series(
        0.0,
        index=dates,
        name="net_trade_flow_krw"
    )

    for _, trade in trades.iterrows():

        trade_date = trade["trade_date"]
        asset_id = trade["asset_id"]
        currency = asset_currency[asset_id]

        fx_rate = fx_matrix.loc[
            trade_date,
            currency
        ]

        trade_value_krw = (
            trade["quantity"]
            * trade["trade_price"]
            * fx_rate
        )

        if trade["trade_type"] == "BUY":
            flows.loc[trade_date] += trade_value_krw
        else:
            flows.loc[trade_date] -= trade_value_krw

    return flows


def build_portfolio_history():

    assets, trades, prices, fx = load_data()

    start_date = max(
        trades["trade_date"].min(),
        prices["price_date"].min(),
        fx["fx_date"].min()
    )

    end_date = min(
        prices["price_date"].max(),
        fx["fx_date"].max()
    )

    # 주말 제외 평일 기준
    dates = pd.date_range(
        start=start_date,
        end=end_date,
        freq="B"
    )

    positions = build_daily_positions(
        assets,
        trades,
        dates
    )

    prices_daily = build_price_matrix(
        assets,
        prices,
        dates
    )

    fx_daily = build_fx_matrix(
        assets,
        fx,
        dates
    )

    market_values = (
        positions
        * prices_daily
        * fx_daily
    )

    # 먼저 포트폴리오 평가액 계산
    portfolio_value = market_values.sum(
        axis=1,
        min_count=1
    )

    # 거래로 인한 자금 유입/유출 계산
    trade_flows = build_daily_trade_flows(
        assets,
        trades,
        fx,
        dates
    )

    previous_value = portfolio_value.shift(1)

    # 거래효과를 제거한 일별 수익률
    daily_return = (
        portfolio_value
        - previous_value
        - trade_flows
    ) / previous_value

    history = pd.DataFrame({
        "date": dates,
        "portfolio_value_krw":
            portfolio_value.values,
        "net_trade_flow_krw":
            trade_flows.values,
        "daily_return":
            daily_return.values
    })

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    history.to_csv(
        OUTPUT_PATH,
        index=False
    )

    return history


if __name__ == "__main__":

    history = build_portfolio_history()

    print("Portfolio history created.")
    print(f"Rows: {len(history)}")

    print()
    print("First 15 rows")
    print(
        history
        .head(15)
        .to_string(index=False)
    )

    print()
    print("Largest daily returns")
    print(
        history
        .dropna(
            subset=["daily_return"]
        )
        .assign(
            abs_return=lambda x:
                x["daily_return"].abs()
        )
        .nlargest(
            10,
            "abs_return"
        )[
            [
                "date",
                "portfolio_value_krw",
                "net_trade_flow_krw",
                "daily_return"
            ]
        ]
        .to_string(index=False)
    )