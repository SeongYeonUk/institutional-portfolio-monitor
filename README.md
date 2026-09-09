# Institutional Portfolio Monitor

글로벌 금융자산의 거래, 포지션, 시장가격과 환율 데이터를 통합하여 평가가치, 손익, 자산 및 통화 익스포저, 리스크를 분석하고 데이터 정합성을 검증하는 금융IT 미니프로젝트입니다.

기관투자자의 투자시스템과 포트폴리오 관리 구조를 이해하는 것을 목적으로 하며, 실제 기관의 포트폴리오를 재현하지 않고 가상의 거래데이터와 공개 시장데이터를 활용했습니다.

## 1. 프로젝트 개요

금융기관의 자산운용 시스템에서는 거래내역만 관리하는 것이 아니라 거래를 현재 포지션으로 집계하고, 시장가격과 환율을 결합하여 평가금액과 손익을 계산해야 합니다.

또한 외부 시장데이터의 결측이나 거래데이터의 오류가 최종 평가결과에 영향을 줄 수 있으므로 데이터 정합성 검증과 계산 결과의 대사가 중요합니다.

본 프로젝트에서는 이를 단순화하여 다음 흐름을 구현했습니다.

```text
Trade
  ↓
Position
  ↓
Market Price + FX Rate
  ↓
Market Value
  ↓
PnL
  ↓
Asset Exposure / Currency Exposure
  ↓
Portfolio Return
  ↓
MDD / Historical VaR
  ↓
Validation / Reconciliation
```

## 2. 프로젝트 목표

다음 질문에 답할 수 있는 간단한 금융자산 포트폴리오 관리 시스템을 구현했습니다.

1. 현재 어떤 자산을 얼마나 보유하고 있는가
2. 현재 포트폴리오 평가금액은 얼마인가
3. 자산별 평가손익은 얼마인가
4. 자산군별 투자비중은 어떻게 구성되어 있는가
5. 통화별 익스포저는 어떻게 구성되어 있는가
6. 포트폴리오 위험은 어느 정도인가
7. 외부 금융데이터와 계산결과에 오류나 누락은 없는가

## 3. 기술 스택

- Python
- Pandas
- SQLite
- SQL
- yfinance
- ECB SDMX API

## 4. 데이터 구성

프로젝트에서는 실제 기관의 투자내역을 사용하지 않습니다.

### 가상 데이터

- 자산 마스터 7개
- 가상 거래 28건

### 실제 공개 데이터

- 시장가격 1,198건
- 환율 700건

시장가격은 공개 시장데이터를 수집하여 사용하고, 환율은 ECB 데이터를 KRW 기준 내부 포맷으로 변환하여 저장했습니다.

### 자산 구성

| 자산 | Symbol | Asset Class | Currency |
| --- | --- | --- | --- |
| 미국 주식 | SPY | Equity | USD |
| 미국 국채 | IEF | Bond | USD |
| 미국 회사채 | LQD | Bond | USD |
| 금 | GLD | Alternative | USD |
| 미국 부동산 | VNQ | Alternative | USD |
| 유럽 주식 | EXSA.DE | Equity | EUR |
| 일본 주식 | 1321.T | Equity | JPY |

## 5. 데이터 모델

원천 데이터는 네 개의 테이블로 구성했습니다.

```text
asset
 ├ asset_id
 ├ symbol
 ├ asset_name
 ├ asset_class
 └ currency

trade
 ├ trade_id
 ├ trade_date
 ├ asset_id
 ├ trade_type
 ├ quantity
 └ trade_price

price
 ├ price_date
 ├ asset_id
 └ close_price

fx_rate
 ├ fx_date
 ├ currency
 └ rate_to_krw
```

Position과 Market Value 등은 별도의 원천 테이블로 저장하지 않고 Trade와 시장데이터를 기반으로 계산합니다.

이를 통해 거래데이터를 원천 데이터로 유지하고 파생데이터와 원천데이터 간 불일치를 최소화했습니다.

## 6. 주요 기능

### 6.1 Position 계산

BUY 거래는 양수, SELL 거래는 음수로 변환한 뒤 자산별 거래수량을 집계하여 현재 Position을 계산했습니다.

```text
Position
= Total BUY Quantity
- Total SELL Quantity
```

### 6.2 평균매입단가

매수 거래의 가중평균 가격을 사용해 평균매입단가를 계산했습니다.

```text
Average Buy Price
= Total BUY Amount
/ Total BUY Quantity
```

본 프로젝트에서는 실제 금융기관의 원가배분 및 회계처리를 단순화하여 적용했습니다.

### 6.3 As-of Valuation

글로벌 시장과 환율 데이터는 서로 다른 영업일을 가질 수 있으므로 평가일과 정확히 같은 데이터가 없는 경우 평가일 이전의 최신 유효값을 사용합니다.

```text
Valuation Date
↓
Latest Valid Price
+
Latest Valid FX Rate
↓
Portfolio Valuation
```

### 6.4 KRW Market Value

외화표시 자산은 현재 Position과 시장가격을 이용해 현지통화 평가금액을 계산한 후 KRW 기준으로 환산했습니다.

```text
Market Value KRW
= Position
× Current Price
× FX Rate
```

### 6.5 Unrealized PnL

현재 시장가격과 평균매입단가의 차이를 이용해 평가손익을 계산했습니다.

```text
Unrealized PnL
= (Current Price - Average Buy Price)
× Position
```

### 6.6 Asset Class Exposure

전체 포트폴리오 평가금액에서 각 자산군이 차지하는 비중을 계산했습니다.

### 6.7 Currency Exposure

USD, EUR, JPY 등 통화별 자산 평가금액을 KRW로 환산한 뒤 전체 포트폴리오에서 차지하는 비중을 계산했습니다.

## 7. Portfolio History

연중 거래가 발생하므로 현재 Position을 과거 전체 기간에 그대로 적용하지 않고 각 날짜까지 발생한 거래만 누적하여 시점별 Position을 계산했습니다.

```text
Trade History
↓
Point-in-Time Position
↓
Price and FX
↓
Daily Portfolio Value
```

이를 통해 미래 거래정보가 과거 평가에 반영되는 Look-ahead 오류를 방지했습니다.

## 8. 거래효과를 제거한 일별 수익률

포트폴리오 가치의 단순 변화율에는 신규 매수와 매도에 따른 자금 유입 및 유출이 포함됩니다.

이를 시장수익률로 잘못 해석하지 않도록 거래효과를 제거한 일별 수익률을 계산했습니다.

```text
Daily Return
=
(Current Portfolio Value
- Previous Portfolio Value
- Net Trade Flow)
/
Previous Portfolio Value
```

## 9. Risk Analysis

### Maximum Drawdown

거래효과가 제거된 일별 수익률을 누적하여 성과지수를 생성하고 직전 최고점 대비 최대 하락폭을 계산했습니다.

결과

- MDD: -12.89%
- Peak Date: 2026-06-04
- Trough Date: 2026-09-08

### Historical VaR

171개의 일별 수익률 관측치를 이용해 95% 신뢰수준의 1일 Historical VaR를 계산했습니다.

결과

- 1-Day Historical VaR 95%: 1.39%
- VaR Amount: 4,259,708 KRW

VaR는 최대손실을 의미하지 않으며 과거 수익률 분포를 기반으로 일정 신뢰수준에서의 1일 손실위험을 나타냅니다.

## 10. 주요 분석 결과

### 평가기준일

2026-09-08

### 총 포트폴리오 평가액

306,897,042.54 KRW

### 총 평가손익

+11,725,825 KRW

### Asset Class Exposure

| Asset Class | Exposure |
| --- | ---: |
| Equity | 62.98% |
| Alternative | 20.72% |
| Bond | 16.30% |

### Currency Exposure

| Currency | Exposure |
| --- | ---: |
| USD | 83.91% |
| JPY | 11.48% |
| EUR | 4.62% |

표시 비중은 소수점 둘째 자리에서 반올림하므로 합계가 100.00%와 미세하게 다를 수 있습니다.

## 11. Data Validation

금융데이터의 오류가 최종 포트폴리오 평가결과에 전파되지 않도록 원천 데이터와 파생 데이터를 별도로 검증했습니다.

### Preventive Control

SQLite의 제약조건을 활용해 잘못된 데이터 입력을 사전에 방지했습니다.

- Primary Key
- Foreign Key
- CHECK Constraint

### Detective Control

다음 항목을 검증했습니다.

- Duplicate Trade
- Invalid Trade Value
- Orphan Trade
- Invalid Price
- Invalid FX Rate
- Negative Position
- Missing Valuation Price
- Missing Valuation FX
- Missing Market Value

## 12. 실제 데이터 문제와 해결

시장가격 데이터를 처리하는 과정에서 EXSA.DE의 2026-09-08 종가가 결측값으로 존재하는 문제를 발견했습니다.

초기 평가 로직에서는 해당 가격이 NULL이 되면서 EXSA.DE의 평가금액이 누락되었고, SQLite의 SUM 함수가 NULL 값을 제외하여 불완전한 포트폴리오 평가액이 정상 숫자처럼 출력되는 문제가 발생했습니다.

이를 다음과 같이 개선했습니다.

```text
Raw Market Data
EXSA.DE 2026-09-08 Close = NULL
↓
Validation
Missing Price Detected
↓
As-of Logic
2026-09-07 Latest Valid Price
↓
Complete Portfolio Valuation
```

원천 데이터의 결측은 그대로 탐지하고 기록하면서 평가 단계에서는 평가일 이전의 최신 유효가격을 사용하도록 구현했습니다.

그 결과 원천 데이터에서는 결측가격 1건을 탐지했지만 최종 평가 데이터에는 누락된 가격이나 평가금액이 존재하지 않았습니다.

## 13. Reconciliation

동일한 포트폴리오 평가액을 서로 다른 계산 경로로 독립 계산한 뒤 결과를 대사했습니다.

### SQL

```text
Trade
↓
Position View
↓
Price and FX Join
↓
Valuation Summary
```

결과

306,897,042.54 KRW

### Python

```text
Trade
↓
Daily Position
↓
Price and FX Matrix
↓
Portfolio History
```

결과

306,897,042.54 KRW

### Reconciliation Result

```text
SQL Value      306,897,042.54 KRW
Python Value   306,897,042.54 KRW
Difference               0.00 KRW

PASS
```

## 14. Validation Summary

```text
PASS      11
HANDLED    1
FAIL       0

OVERALL STATUS: PASS
```

원천 시장가격 결측 1건은 Validation에서 탐지한 뒤 As-of 로직으로 정상 처리했습니다.

## 15. 프로젝트 구조

```text
institutional-portfolio-monitor
│
├── README.md
├── requirements.txt
│
├── data
│   ├── raw
│   │   ├── assets.csv
│   │   └── trades.csv
│   ├── cache
│   │   ├── prices.csv
│   │   └── fx_rates.csv
│   └── processed
│       └── portfolio_history.csv
│
├── db
│   └── portfolio.db
│
├── sql
│   ├── schema.sql
│   ├── portfolio_queries.sql
│   └── validation_queries.sql
│
└── src
    ├── fetch_prices.py
    ├── fetch_fx.py
    ├── generate_trades.py
    ├── init_db.py
    ├── create_views.py
    ├── run_query.py
    ├── portfolio.py
    ├── risk.py
    └── validation.py
```

## 16. 실행 방법

가상환경 생성 후 필요한 패키지를 설치합니다.

```bash
python -m venv .venv
pip install -r requirements.txt
```

데이터 수집 및 분석은 다음 순서로 실행합니다.

```bash
python src/fetch_prices.py
python src/fetch_fx.py
python src/generate_trades.py
python src/init_db.py
python src/create_views.py
python src/portfolio.py
python src/risk.py
python src/validation.py
```

## 17. 프로젝트의 한계

본 프로젝트는 기관투자자의 금융IT 업무구조를 학습하기 위해 실제 업무를 단순화한 프로젝트입니다.

다음 요소는 구현 범위에서 제외했습니다.

- 실제 기관의 포트폴리오 및 거래데이터
- 주문 및 체결 시스템
- 결제 시스템
- 거래수수료 및 세금
- 실제 회계기준에 따른 원가배분
- 현금계정
- 실현손익
- 파생상품
- 실제 펀드 NAV 계산
- 정교한 시장별 영업일 캘린더
- 배당을 포함한 Total Return
- 기관용 리스크 모델

따라서 본 프로젝트의 결과값은 투자판단이나 실제 기관의 자산운용 분석을 목적으로 하지 않습니다.

## 18. 향후 확장 방향

### 기관투자 포트폴리오 관리

Target Allocation과 Actual Allocation을 비교하고 자산배분 이탈 수준을 분석할 수 있습니다.

### 환율 시나리오 분석

USD, EUR, JPY 환율 변동 시 KRW 기준 포트폴리오 가치 변화 분석 기능을 추가할 수 있습니다.

### Benchmark 분석

포트폴리오 수익률과 기준지수 수익률을 비교하여 초과성과를 분석할 수 있습니다.

### 데이터 품질관리

가격 및 환율 데이터의 이상치 탐지, 데이터 수집 로그, Data Lineage 관리 기능으로 확장할 수 있습니다.

## 19. 학습 내용

프로젝트를 통해 다음 금융IT 개념을 학습하고 구현했습니다.

- Trade
- Position
- Point-in-Time Position
- Average Cost
- Market Value
- PnL
- Asset Exposure
- Currency Exposure
- As-of Valuation
- MDD
- Historical VaR
- Data Validation
- Reconciliation
- Data Lineage

특히 금융IT에서는 분석기능 자체뿐 아니라 입력 데이터의 정확성과 최종 계산결과의 정합성을 함께 관리해야 한다는 점을 확인했습니다.