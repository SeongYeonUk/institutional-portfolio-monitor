from pathlib import Path
from datetime import date
from io import StringIO

import pandas as pd
import requests


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_PATH = BASE_DIR / "data" / "cache" / "fx_rates.csv"

START_DATE = "2026-01-01"
END_DATE = date.today().isoformat()

ECB_URL = (
    "https://data-api.ecb.europa.eu/service/data/"
    "EXR/D.USD+JPY+KRW.EUR.SP00.A"
)


def fetch_fx():
    params = {
        "startPeriod": START_DATE,
        "endPeriod": END_DATE,
        "format": "csvdata",
        "detail": "dataonly"
    }

    response = requests.get(
        ECB_URL,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    raw = pd.read_csv(StringIO(response.text))

    needed = raw[
        ["TIME_PERIOD", "CURRENCY", "OBS_VALUE"]
    ].copy()

    needed["TIME_PERIOD"] = pd.to_datetime(
        needed["TIME_PERIOD"]
    )

    pivot = needed.pivot(
        index="TIME_PERIOD",
        columns="CURRENCY",
        values="OBS_VALUE"
    )

    # 필요한 세 환율이 모두 있는 날짜만 사용
    pivot = pivot.dropna(
        subset=["USD", "JPY", "KRW"]
    )

    result = []

    for fx_date, row in pivot.iterrows():

        krw_per_eur = row["KRW"]
        usd_per_eur = row["USD"]
        jpy_per_eur = row["JPY"]

        result.extend([
            {
                "fx_date": fx_date.date().isoformat(),
                "currency": "USD",
                "rate_to_krw": krw_per_eur / usd_per_eur
            },
            {
                "fx_date": fx_date.date().isoformat(),
                "currency": "EUR",
                "rate_to_krw": krw_per_eur
            },
            {
                "fx_date": fx_date.date().isoformat(),
                "currency": "JPY",
                "rate_to_krw": krw_per_eur / jpy_per_eur
            },
            {
                "fx_date": fx_date.date().isoformat(),
                "currency": "KRW",
                "rate_to_krw": 1.0
            }
        ])

    fx = pd.DataFrame(result)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fx.to_csv(OUTPUT_PATH, index=False)

    print("FX data saved.")
    print(f"Rows: {len(fx)}")
    print(fx.head(8))


if __name__ == "__main__":
    fetch_fx()