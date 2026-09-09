from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

HISTORY_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "portfolio_history.csv"
)


def load_history():
    history = pd.read_csv(
        HISTORY_PATH,
        parse_dates=["date"]
    )

    return history


def calculate_drawdown(history):
    result = history.copy()

    # 첫날 수익률 NaN은 0으로 처리
    result["daily_return"] = (
        result["daily_return"].fillna(0.0)
    )

    # 거래효과가 제거된 수익률을 누적해 성과지수 생성
    result["wealth_index"] = (
        1.0 + result["daily_return"]
    ).cumprod()

    # 각 시점까지의 최고 성과
    result["running_peak"] = (
        result["wealth_index"].cummax()
    )

    # 최고점 대비 현재 하락률
    result["drawdown"] = (
        result["wealth_index"]
        / result["running_peak"]
        - 1.0
    )

    return result

def calculate_mdd(drawdown_data):

    trough_index = (
        drawdown_data["drawdown"].idxmin()
    )

    mdd = drawdown_data.loc[
        trough_index,
        "drawdown"
    ]

    trough_date = drawdown_data.loc[
        trough_index,
        "date"
    ]

    peak_data = drawdown_data.loc[
        :trough_index
    ]

    peak_index = (
        peak_data["wealth_index"].idxmax()
    )

    peak_date = drawdown_data.loc[
        peak_index,
        "date"
    ]

    return {
        "mdd": mdd,
        "peak_date": peak_date,
        "trough_date": trough_date
    }

def calculate_historical_var(
    history,
    confidence_level=0.95
):
    returns = (
        history["daily_return"]
        .dropna()
    )

    tail_probability = (
        1.0 - confidence_level
    )

    return_quantile = returns.quantile(
        tail_probability
    )

    var_pct = -return_quantile

    current_value = (
        history["portfolio_value_krw"]
        .iloc[-1]
    )

    var_krw = (
        current_value
        * var_pct
    )

    return {
        "confidence_level": confidence_level,
        "return_quantile": return_quantile,
        "var_pct": var_pct,
        "var_krw": var_krw,
        "observation_count": len(returns)
    }

if __name__ == "__main__":

    history = load_history()

    drawdown_data = calculate_drawdown(
        history
    )

    mdd_result = calculate_mdd(
        drawdown_data
    )

    print("Risk Analysis")
    print()

    print(
        f"MDD: "
        f"{mdd_result['mdd']:.2%}"
    )

    print(
        "Peak Date: "
        f"{mdd_result['peak_date'].date()}"
    )

    print(
        "Trough Date: "
        f"{mdd_result['trough_date'].date()}"
    )

    print()

    print("Worst Drawdown Days")

    print(
        drawdown_data[
            [
                "date",
                "wealth_index",
                "drawdown"
            ]
        ]
        .nsmallest(
            10,
            "drawdown"
        )
        .to_string(
            index=False
        )
    )
    
    var_result = calculate_historical_var(
    history,
    confidence_level=0.95
    )

    print()
    print("Historical VaR")
    print()

    print(
        "Confidence Level: "
        f"{var_result['confidence_level']:.0%}"
    )

    print(
        "Observations: "
        f"{var_result['observation_count']}"
    )

    print(
        "1-Day VaR: "
        f"{var_result['var_pct']:.2%}"
    )

    print(
        "1-Day VaR KRW: "
        f"{var_result['var_krw']:,.0f}"
    )