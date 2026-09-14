# Institutional Portfolio Monitor

글로벌 금융자산의 거래, 포지션, 시장가격과 환율 데이터를 통합하여 평가가치, 손익, 자산 및 통화 익스포저, 리스크를 분석하고 데이터 정합성을 검증하는 금융IT 미니프로젝트입니다.

초기에는 기관투자자의 투자시스템과 포트폴리오 관리 구조를 이해하는 것을 목적으로 거래, 포지션, 시장가격, 환율, 평가손익, 리스크 관리 기능을 구현했습니다.

이후 자본시장 금융IT 업무에 대한 이해를 확장하기 위해 증권거래의 주문, 체결, 결제, 포지션 및 현금 반영 과정을 추가했습니다. 정상 거래뿐 아니라 결제 실패, 중복 처리, 원장 불일치 등을 검증하고 운영 상태를 모니터링할 수 있도록 확장했습니다.

실제 금융기관의 포트폴리오나 거래정보를 재현하지 않으며, 가상의 거래데이터와 공개 시장데이터를 활용한 학습 목적의 프로젝트입니다.

---

## 1. 프로젝트 개요

금융기관의 자산운용 시스템에서는 거래내역만 관리하는 것이 아니라 거래를 현재 포지션으로 집계하고, 시장가격과 환율을 결합하여 평가금액과 손익을 계산해야 합니다.

또한 외부 시장데이터의 결측이나 거래데이터의 오류가 최종 평가결과에 영향을 줄 수 있으므로 데이터 품질 검증과 서로 다른 계산 경로 간 대사가 중요합니다.

본 프로젝트의 초기 포트폴리오 분석 흐름은 다음과 같습니다.

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

이후 증권거래 운영 영역을 다음과 같이 확장했습니다.

```text
Order
  ↓
Execution
  ↓
Pending Settlement
  ↓
Settled / Failed
  ↓
Position + Cash
  ↓
Reconciliation
  ↓
Operations Monitoring
```

즉, 현재 프로젝트는 크게 두 영역으로 구성됩니다.

```text
Institutional Portfolio Monitor
│
├─ Portfolio Management
│  ├─ Trade / Position
│  ├─ Market Price / FX
│  ├─ Valuation / PnL
│  ├─ Exposure
│  ├─ Return / Risk
│  └─ Data Validation
│
└─ Securities Operations
   ├─ Order
   ├─ Execution
   ├─ Settlement
   ├─ Position / Cash
   ├─ Idempotency
   ├─ Exception Handling
   ├─ Reconciliation
   └─ Operations Monitoring
```

---

## 2. 프로젝트 목표

다음 질문에 답할 수 있는 간단한 금융자산 관리 및 증권거래 운영 시스템을 구현했습니다.

1. 현재 어떤 자산을 얼마나 보유하고 있는가
2. 현재 포트폴리오 평가금액은 얼마인가
3. 자산별 평가손익은 얼마인가
4. 자산군별 투자비중은 어떻게 구성되어 있는가
5. 통화별 익스포저는 어떻게 구성되어 있는가
6. 포트폴리오 위험은 어느 정도인가
7. 외부 금융데이터와 계산결과에 오류나 누락은 없는가
8. 주문이 어떤 체결 및 결제 상태에 있는가
9. 결제된 거래가 포지션과 현금에 정확히 반영되었는가
10. 동일 거래가 중복 반영되지 않았는가
11. 실패한 거래가 실제 원장을 오염시키지 않았는가
12. 운영자가 미결제, 실패, 정합성 이상을 확인할 수 있는가

---

## 3. 기술 스택

* Python
* Pandas
* SQLite
* SQL
* yfinance
* ECB SDMX API

---

# Part 1. Portfolio Management

## 4. 데이터 구성

프로젝트에서는 실제 기관의 투자내역을 사용하지 않습니다.

### 가상 데이터

* 자산 마스터 7개
* 초기 가상 거래 28건

### 실제 공개 데이터

* 시장가격 1,198건
* 환율 700건

시장가격은 공개 시장데이터를 수집하여 사용하고, 환율은 ECB 데이터를 KRW 기준 내부 포맷으로 변환하여 저장했습니다.

### 자산 구성

| 자산     | Symbol  | Asset Class | Currency |
| ------ | ------- | ----------- | -------- |
| 미국 주식  | SPY     | Equity      | USD      |
| 미국 국채  | IEF     | Bond        | USD      |
| 미국 회사채 | LQD     | Bond        | USD      |
| 금      | GLD     | Alternative | USD      |
| 미국 부동산 | VNQ     | Alternative | USD      |
| 유럽 주식  | EXSA.DE | Equity      | EUR      |
| 일본 주식  | 1321.T  | Equity      | JPY      |

---

## 5. 기본 데이터 모델

기존 포트폴리오 분석의 원천 데이터는 네 개의 테이블로 구성했습니다.

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

---

## 6. 주요 포트폴리오 기능

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

---

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

---

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

---

## 9. Risk Analysis

### Maximum Drawdown

거래효과가 제거된 일별 수익률을 누적하여 성과지수를 생성하고 직전 최고점 대비 최대 하락폭을 계산했습니다.

결과:

* MDD: -12.89%
* Peak Date: 2026-06-04
* Trough Date: 2026-09-08

### Historical VaR

171개의 일별 수익률 관측치를 이용해 95% 신뢰수준의 1일 Historical VaR를 계산했습니다.

결과:

* 1-Day Historical VaR 95%: 1.39%
* VaR Amount: 4,259,708 KRW

VaR는 최대손실을 의미하지 않으며 과거 수익률 분포를 기반으로 일정 신뢰수준에서의 1일 손실위험을 나타냅니다.

---

## 10. 주요 분석 결과

### 평가기준일

2026-09-08

### 총 포트폴리오 평가액

306,897,042.54 KRW

### 총 평가손익

+11,725,825 KRW

### Asset Class Exposure

| Asset Class | Exposure |
| ----------- | -------: |
| Equity      |   62.98% |
| Alternative |   20.72% |
| Bond        |   16.30% |

### Currency Exposure

| Currency | Exposure |
| -------- | -------: |
| USD      |   83.91% |
| JPY      |   11.48% |
| EUR      |    4.62% |

표시 비중은 소수점 둘째 자리에서 반올림하므로 합계가 100.00%와 미세하게 다를 수 있습니다.

---

## 11. Data Validation

금융데이터의 오류가 최종 포트폴리오 평가결과에 전파되지 않도록 원천 데이터와 파생 데이터를 별도로 검증했습니다.

### Preventive Control

SQLite의 제약조건을 활용해 잘못된 데이터 입력을 사전에 방지했습니다.

* Primary Key
* Foreign Key
* CHECK Constraint

### Detective Control

다음 항목을 검증했습니다.

* Duplicate Trade
* Invalid Trade Value
* Orphan Trade
* Invalid Price
* Invalid FX Rate
* Negative Position
* Missing Valuation Price
* Missing Valuation FX
* Missing Market Value

---

## 12. 실제 데이터 문제와 해결

시장가격 데이터를 처리하는 과정에서 EXSA.DE의 2026-09-08 종가가 결측값으로 존재하는 문제를 발견했습니다.

초기 평가 로직에서는 해당 가격이 NULL이 되면서 EXSA.DE의 평가금액이 누락되었고, SQLite의 SUM 함수가 NULL 값을 제외하여 불완전한 포트폴리오 평가액이 정상 숫자처럼 출력되는 문제가 발생했습니다.

이를 다음과 같이 개선했습니다.

```text
Raw Market Data

EXSA.DE
2026-09-08 Close = NULL

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

---

## 13. Portfolio Reconciliation

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

결과:

```text
306,897,042.54 KRW
```

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

결과:

```text
306,897,042.54 KRW
```

### Reconciliation Result

```text
SQL Value      306,897,042.54 KRW
Python Value   306,897,042.54 KRW
Difference               0.00 KRW

PASS
```

---

## 14. Portfolio Validation Summary

```text
PASS      11
HANDLED    1
FAIL       0

OVERALL STATUS: PASS
```

원천 시장가격 결측 1건은 Validation에서 탐지한 뒤 As-of 로직으로 정상 처리했습니다.

---

# Part 2. Securities Operations Extension

## 15. 증권거래 운영 확장 개요

기존 프로젝트에서는 이미 생성된 Trade를 기준으로 포지션과 평가금액을 분석했습니다.

이번 확장에서는 Trade가 최종 원장에 기록되기 이전의 과정을 단순화하여 구현했습니다.

```text
Order
  ↓
Execution
  ↓
Settlement
  ↓
Portfolio Trade
  +
Cash Ledger
```

핵심 목표는 단순 주문 기능 구현보다 다음 금융IT 운영 요소를 학습하는 것이었습니다.

* 거래 상태 관리
* 결제 전 검증
* 포지션과 현금의 일관성
* 중복처리 방지
* 실패 거래 격리
* 원장 간 대사
* 운영 상태 모니터링

---

## 16. Securities Data Model

증권거래 확장을 위해 다음 테이블을 추가했습니다.

### securities_orders

```text
securities_orders
 ├ order_id
 ├ symbol
 ├ side
 ├ order_quantity
 ├ order_price
 ├ currency
 ├ order_status
 ├ ordered_at
 └ created_at
```

### securities_executions

```text
securities_executions
 ├ execution_id
 ├ order_id
 ├ executed_quantity
 ├ executed_price
 └ executed_at
```

현재 1차 구현에서는 하나의 주문이 하나의 전체 체결로 연결되는 구조로 단순화했습니다.

### securities_settlements

```text
securities_settlements
 ├ settlement_id
 ├ execution_id
 ├ settlement_date
 ├ settlement_amount
 ├ currency
 ├ settlement_status
 ├ failure_reason
 ├ settled_at
 ├ portfolio_applied
 ├ applied_trade_id
 └ applied_at
```

### securities_cash_ledger

```text
securities_cash_ledger
 ├ cash_entry_id
 ├ settlement_id
 ├ currency
 ├ amount
 ├ entry_type
 └ created_at
```

---

## 17. Order / Execution / Settlement

### 17.1 Order

주문 생성 시 다음 정보를 기록합니다.

* Order ID
* Symbol
* BUY / SELL
* Quantity
* Order Price
* Currency

주문 생성 직후 상태는 다음과 같습니다.

```text
ORDERED
```

### 17.2 Execution

주문이 체결되면 별도의 Execution 데이터를 생성합니다.

```text
ORDERED
   ↓
EXECUTED
```

주문가격과 실제 체결가격을 분리하여 기록합니다.

예:

```text
Order Price     600.0 USD
Executed Price  598.5 USD
```

현재 구현에서는 부분체결을 제외하고 전체수량이 한 번에 체결되는 흐름으로 단순화했습니다.

### 17.3 Settlement

체결 거래는 결제대기 상태로 생성됩니다.

```text
PENDING
```

결제조건을 충족하면:

```text
PENDING
   ↓
SETTLED
```

조건을 충족하지 못하면:

```text
PENDING
   ↓
FAILED
```

상태로 전환됩니다.

---

## 18. Settlement Validation

결제를 완료하기 전 BUY와 SELL에 필요한 조건을 확인합니다.

### BUY

BUY 거래는 결제금액보다 충분한 현금이 존재하는지 확인합니다.

```text
Available Cash
>= Settlement Amount
```

조건을 만족하지 못하면:

```text
FAILED
Reason: INSUFFICIENT_CASH
```

로 처리합니다.

### SELL

SELL 거래는 실제 보유수량보다 매도수량이 많지 않은지 확인합니다.

```text
Current Position
>= Sell Quantity
```

조건을 만족하지 못하면:

```text
FAILED
Reason: INSUFFICIENT_POSITION
```

로 처리합니다.

---

## 19. Position and Cash Settlement

결제가 `SETTLED` 상태가 된 거래만 실제 포트폴리오에 반영합니다.

### BUY

```text
BUY
 ↓
Position +
Cash -
```

테스트 예:

```text
BUY SPY 10 @ 598.5 USD

SPY Position
140 → 150

USD Cash
100000 → 94015
```

### SELL

```text
SELL
 ↓
Position -
Cash +
```

테스트 예:

```text
SELL SPY 5 @ 610 USD

SPY Position
150 → 145

USD Cash
94015 → 97065
```

---

## 20. Transaction Consistency

포트폴리오의 Trade 반영과 Cash Ledger 반영은 동일한 데이터베이스 트랜잭션 안에서 처리합니다.

```text
BEGIN TRANSACTION

1. Portfolio Trade Insert
2. Cash Ledger Insert
3. Settlement Applied Flag Update

COMMIT
```

중간 단계에서 오류가 발생하면 전체 작업이 롤백될 수 있도록 구성하여 다음과 같은 부분처리를 방지하는 것을 목표로 했습니다.

```text
Position Updated
Cash Not Updated
```

또는

```text
Cash Updated
Position Not Updated
```

금융거래에서는 두 원장이 함께 일관된 상태를 유지하는 것이 중요하다는 점을 반영했습니다.

---

## 21. Cash Ledger

현재 현금잔액을 단일 값으로 덮어쓰지 않고 모든 현금변동을 원장으로 기록합니다.

예:

```text
OPENING     +100000
BUY           -5985
SELL          +3050
```

최종 현금잔액은 다음과 같이 계산합니다.

```text
Cash Balance
= SUM(Cash Ledger Amount)
```

이를 통해 최종 잔액뿐 아니라 어떤 거래 때문에 현금이 증가하거나 감소했는지도 추적할 수 있습니다.

---

## 22. Idempotency

금융시스템에서는 요청을 처리한 뒤 응답이 유실되면 동일 요청이 다시 전달될 수 있습니다.

이때 같은 거래를 두 번 반영하면 포지션과 현금이 모두 왜곡될 수 있습니다.

예:

```text
STL001
 ↓
SPY +10
USD -5985
```

동일한 Settlement가 다시 요청되어도:

```text
STL001
 ↓
Already Applied
 ↓
SKIP
```

되도록 구현했습니다.

실행 결과 예:

```text
[PORTFOLIO SKIPPED]
STL001 already applied as SEC_STL001
```

Settlement에 다음 정보를 기록합니다.

```text
portfolio_applied
applied_trade_id
applied_at
```

또한 Cash Ledger의 settlement_id에 고유성을 두어 동일 Settlement의 현금변동이 중복 기록되는 것도 방지했습니다.

---

## 23. Exception Handling

정상 거래뿐 아니라 여러 실패 시나리오를 별도로 테스트했습니다.

### 23.1 PENDING Settlement

아직 결제가 완료되지 않은 거래는 실제 포트폴리오에 반영할 수 없습니다.

```text
PENDING
 ↓
Portfolio Application
 ↓
REJECT
```

### 23.2 Insufficient Cash

현금 100,000 USD 상태에서 1,000,000 USD 규모의 BUY 결제를 시도했습니다.

```text
Required Cash  1,000,000 USD
Current Cash     100,000 USD
```

결과:

```text
Settlement Status : FAILED
Failure Reason    : INSUFFICIENT_CASH
Portfolio Applied : 0
```

### 23.3 Insufficient Position

SPY 140주를 보유한 상태에서 99,999주를 SELL하도록 테스트했습니다.

결과:

```text
Settlement Status : FAILED
Failure Reason    : INSUFFICIENT_POSITION
Portfolio Applied : 0
```

### 23.4 Ledger Integrity

두 실패 시나리오 이후 실제 원장을 확인했습니다.

```text
SPY Position  140
USD Cash      100000
```

실패 이전과 값이 동일하게 유지되었습니다.

그 이후 정상 BUY 거래를 실행한 결과:

```text
BUY SPY 2 @ 500 USD

SPY Position
140 → 142

USD Cash
100000 → 99000
```

으로 정상 거래가 다시 처리되는 것도 확인했습니다.

---

## 24. Securities Reconciliation

정상적으로 처리됐다는 메시지만 확인하지 않고 증권거래 원천 데이터와 실제 포트폴리오 원장을 독립적으로 비교했습니다.

### 24.1 Trade Detail Reconciliation

Settlement와 Execution 정보를 실제 Trade 원장과 비교합니다.

검증 항목:

* Trade 존재 여부
* Trade Date
* Asset
* BUY / SELL
* Quantity
* Price

정상 결과:

```text
Trade Detail Reconciliation
PASS
```

### 24.2 Cash Detail Reconciliation

Settlement 기준 예상 현금변동과 실제 Cash Ledger를 비교합니다.

BUY:

```text
Expected Cash Flow
= -Settlement Amount
```

SELL:

```text
Expected Cash Flow
= +Settlement Amount
```

정상 결과:

```text
Cash Detail Reconciliation
PASS
```

### 24.3 Position Reconciliation

초기 Portfolio Trade와 신규 Securities Settlement 데이터를 각각 이용해 예상 포지션을 독립적으로 계산한 뒤 실제 Trade 원장의 포지션과 비교합니다.

실행 결과:

```text
1321.T     expected=60       actual=60
EXSA.DE    expected=140      actual=140
GLD        expected=85       actual=85
IEF        expected=210      actual=210
LQD        expected=170      actual=170
SPY        expected=145      actual=145
VNQ        expected=140      actual=140

Result: PASS
```

### 24.4 Cash Balance Reconciliation

초기 현금과 Settlement 기준 예상 현금흐름을 합산하여 실제 Cash Ledger와 비교합니다.

```text
USD
expected=97065.00
actual=97065.00

Result: PASS
```

### 24.5 Overall Result

```text
Trade Detail Reconciliation    PASS
Cash Detail Reconciliation     PASS
Position Reconciliation        PASS
Cash Balance Reconciliation    PASS

OVERALL RECONCILIATION: PASS
```

---

## 25. Operations Monitoring

운영자가 여러 테이블을 직접 조회하지 않고 시스템의 현재 상태를 빠르게 확인할 수 있도록 운영 리포트를 구현했습니다.

### Order / Execution

다음 항목을 집계합니다.

* Total Orders
* ORDERED
* EXECUTED
* Total Executions

### Settlement

다음 상태를 집계합니다.

* Total Settlements
* PENDING
* SETTLED
* FAILED

### Portfolio Application

* Applied
* Not Applied

### Cash Balance

Cash Ledger를 통화별로 집계합니다.

### Failure Summary

결제 실패 사유를 유형별로 집계합니다.

예:

```text
INSUFFICIENT_CASH
INSUFFICIENT_POSITION
```

### Pending / Failed Settlement

운영자가 즉시 확인해야 할 미처리 거래와 실패 거래를 별도로 출력합니다.

### Reconciliation

운영 리포트 실행 시 Securities Reconciliation도 함께 수행합니다.

---

## 26. Operations Monitoring Result

정상 BUY와 SELL 거래를 처리한 이후 운영 리포트 결과는 다음과 같습니다.

```text
[Order / Execution]

Total Orders       : 2
ORDERED            : 0
EXECUTED           : 2
Total Executions   : 2
```

```text
[Settlement]

Total Settlements  : 2
PENDING            : 0
SETTLED            : 2
FAILED             : 0
```

```text
[Portfolio Application]

Applied            : 2
Not Applied        : 0
```

```text
[Cash Balance]

USD : 97065.00
```

```text
[Failure Summary]

No settlement failures
```

정합성 검증 결과:

```text
OVERALL RECONCILIATION: PASS
```

최종 운영상태:

```text
OPERATIONS STATUS: NORMAL
```

---

## 27. 프로젝트 구조

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
│   │
│   ├── cache
│   │   ├── prices.csv
│   │   └── fx_rates.csv
│   │
│   └── processed
│       └── portfolio_history.csv
│
├── db
│   └── portfolio.db
│
├── sql
│   ├── schema.sql
│   ├── securities_schema.sql
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
    ├── validation.py
    ├── securities.py
    ├── reconciliation.py
    ├── operations_report.py
    ├── test_securities.py
    └── test_securities_exceptions.py
```

---

## 28. 실행 방법

### 28.1 가상환경 및 패키지 설치

```bash
python -m venv .venv
pip install -r requirements.txt
```

### 28.2 시장데이터 수집

```bash
python src/fetch_prices.py
python src/fetch_fx.py
```

### 28.3 초기 거래 생성

```bash
python src/generate_trades.py
```

### 28.4 데이터베이스 초기화

```bash
python src/init_db.py
```

초기화 시 기존 DB를 새로 생성하고 다음 데이터를 적재합니다.

```text
asset                  7
trade                  28
price                1198
fx_rate               700
securities_orders       0
securities_executions   0
securities_settlements  0
```

### 28.5 기존 Portfolio 분석

```bash
python src/create_views.py
python src/portfolio.py
python src/risk.py
python src/validation.py
```

### 28.6 Securities 정상 거래 테스트

```bash
python src/test_securities.py
```

테스트 내용:

```text
Opening Cash
   ↓
BUY
   ↓
Settlement
   ↓
Position + Cash
   ↓
Idempotency
   ↓
SELL
   ↓
Position + Cash
```

### 28.7 Securities 예외 테스트

```bash
python src/test_securities_exceptions.py
```

검증 내용:

* PENDING 거래 반영 차단
* 현금 부족 BUY 실패
* 보유수량 부족 SELL 실패
* 실패 거래의 원장 미반영
* 실패 이후 정상 거래 가능 여부

### 28.8 Securities Reconciliation

```bash
python src/reconciliation.py
```

### 28.9 Operations Monitoring

```bash
python src/operations_report.py
```

---

## 29. 검증 요약

### 기존 Portfolio Validation

```text
PASS      11
HANDLED    1
FAIL       0

OVERALL STATUS: PASS
```

### Securities Normal Flow

```text
Initial SPY Position : 140
Initial USD Cash     : 100000

BUY SPY 10 @ 598.5
SPY Position         : 150
USD Cash             : 94015

SELL SPY 5 @ 610
SPY Position         : 145
USD Cash             : 97065
```

### Securities Exception Flow

```text
PENDING Application
→ Rejected

Insufficient Cash
→ FAILED

Insufficient Position
→ FAILED

Failed Transactions
→ No Position Change
→ No Cash Change
```

### Securities Reconciliation

```text
Trade Detail      PASS
Cash Detail       PASS
Position          PASS
Cash Balance      PASS

OVERALL RECONCILIATION: PASS
```

### Operations Monitoring

```text
OPERATIONS STATUS: NORMAL
```

---

## 30. 프로젝트의 한계

본 프로젝트는 기관투자자의 금융IT 및 자본시장 거래 운영 구조를 학습하기 위해 실제 업무를 단순화한 프로젝트입니다.

실제 금융기관의 시스템을 재현하지 않으며 다음과 같은 요소는 구현 범위에서 제외하거나 단순화했습니다.

* 실제 기관의 포트폴리오 및 거래데이터
* 실제 거래소 및 증권사 시스템 연계
* 실제 주문 라우팅
* 실제 Matching Engine
* FIX Protocol
* 부분체결
* 미체결 주문 관리
* 주문 취소 및 정정
* 거래수수료 및 세금
* 실제 회계기준에 따른 원가배분
* 실현손익
* 파생상품
* 실제 펀드 NAV 계산
* 정교한 시장별 영업일 캘린더
* 배당을 포함한 Total Return
* 기관용 리스크 모델
* 실시간 메시지 처리
* 실제 청산 및 결제기관 연계
* 장애복구 및 분산 트랜잭션

따라서 프로젝트에서 구현한 주문, 체결, 결제 과정은 실제 시장 인프라를 그대로 재현한 것이 아니라 거래 정합성과 운영 안정성에 초점을 둔 단순화된 모델입니다.

또한 프로젝트의 결과값은 투자판단이나 실제 기관의 자산운용 분석을 목적으로 하지 않습니다.

---

## 31. 향후 확장 방향

### 31.1 기관투자 포트폴리오 관리

Target Allocation과 Actual Allocation을 비교하고 자산배분 이탈 수준을 분석할 수 있습니다.

### 31.2 환율 시나리오 분석

USD, EUR, JPY 환율 변동 시 KRW 기준 포트폴리오 가치 변화 분석 기능을 추가할 수 있습니다.

### 31.3 Benchmark 분석

포트폴리오 수익률과 기준지수 수익률을 비교하여 초과성과를 분석할 수 있습니다.

### 31.4 데이터 품질관리

다음 기능으로 확장할 수 있습니다.

* 가격 및 환율 이상치 탐지
* 데이터 수집 로그
* Data Lineage
* Validation History
* 장애 및 오류 로그

### 31.5 증권사 업무 확장

증권사 관점으로 확장할 경우 다음 기능을 추가할 수 있습니다.

* 고객 계좌
* 고객별 예수금
* 주문가능금액
* 부분체결
* 미체결 주문
* 주문 취소 및 정정
* 고객별 포지션
* 주문 및 체결 이력 조회

### 31.6 증권금융 업무 확장

증권금융 업무를 학습할 경우 다음 기능을 고려할 수 있습니다.

* 증권대차
* 담보 관리
* 담보가치 평가
* Haircut
* Margin Check
* 증권 반환

---

## 32. 학습 내용

프로젝트를 통해 다음 금융IT 개념을 학습하고 직접 구현했습니다.

### Portfolio Management

* Trade
* Position
* Point-in-Time Position
* Average Cost
* Market Value
* PnL
* Asset Exposure
* Currency Exposure
* As-of Valuation
* Portfolio Return
* MDD
* Historical VaR

### Data Management

* Data Validation
* Reconciliation
* Data Lineage
* Preventive Control
* Detective Control
* Missing Data Handling

### Securities Operations

* Order
* Execution
* Settlement
* Position Settlement
* Cash Ledger
* Transaction Consistency
* Idempotency
* Settlement Failure Handling
* Insufficient Cash Control
* Insufficient Position Control
* Trade Reconciliation
* Cash Reconciliation
* Operations Monitoring

특히 이번 프로젝트를 통해 금융IT에서는 정상 기능 자체를 구현하는 것만큼 다음 요소가 중요하다는 점을 확인했습니다.

```text
정확한 원천 데이터
        +
거래 상태 관리
        +
트랜잭션 일관성
        +
중복 처리 방지
        +
예외 및 실패 격리
        +
원장 간 정합성 검증
        +
운영 상태 모니터링
```

단순히 결과값을 계산하는 시스템에서 나아가, 거래가 어떤 과정을 거쳐 최종 원장에 반영되고 오류가 발생했을 때 데이터의 무결성을 어떻게 유지할 수 있는지까지 구현한 것이 이번 확장의 핵심입니다.
