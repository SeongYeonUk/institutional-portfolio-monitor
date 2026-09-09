DROP VIEW IF EXISTS position_summary;

CREATE VIEW position_summary AS

SELECT
    a.asset_id,
    a.symbol,
    a.asset_name,
    a.asset_class,
    a.currency,

    SUM(
        CASE
            WHEN t.trade_type = 'BUY'
            THEN t.quantity
            ELSE -t.quantity
        END
    ) AS position,

    SUM(
        CASE
            WHEN t.trade_type = 'BUY'
            THEN t.quantity * t.trade_price
            ELSE 0
        END
    )
    /
    SUM(
        CASE
            WHEN t.trade_type = 'BUY'
            THEN t.quantity
            ELSE 0
        END
    ) AS average_buy_price

FROM trade t

JOIN asset a
    ON t.asset_id = a.asset_id

GROUP BY
    a.asset_id,
    a.symbol,
    a.asset_name,
    a.asset_class,
    a.currency;


DROP VIEW IF EXISTS valuation_summary;

CREATE VIEW valuation_summary AS

WITH valuation_date AS (
    SELECT MIN(
        (SELECT MAX(price_date) FROM price),
        (SELECT MAX(fx_date) FROM fx_rate)
    ) AS valuation_date
),

latest_price AS (
    SELECT
        p.asset_id,
        p.price_date,
        p.close_price
    FROM price p
    CROSS JOIN valuation_date vd
    WHERE p.price_date = (
        SELECT MAX(p2.price_date)
        FROM price p2
        WHERE p2.asset_id = p.asset_id
          AND p2.price_date <= vd.valuation_date
          AND p2.close_price IS NOT NULL
          AND p2.close_price > 0
    )
),

latest_fx AS (
    SELECT
        f.currency,
        f.fx_date,
        f.rate_to_krw
    FROM fx_rate f
    CROSS JOIN valuation_date vd
    WHERE f.fx_date = (
        SELECT MAX(f2.fx_date)
        FROM fx_rate f2
        WHERE f2.currency = f.currency
          AND f2.fx_date <= vd.valuation_date
          AND f2.rate_to_krw IS NOT NULL
          AND f2.rate_to_krw > 0
    )
)

SELECT
    vd.valuation_date,

    ps.asset_id,
    ps.symbol,
    ps.asset_name,
    ps.asset_class,
    ps.currency,

    ps.position,
    ps.average_buy_price,

    lp.price_date,
    lp.close_price AS current_price,

    lf.fx_date,
    lf.rate_to_krw,

    ps.position
        * lp.close_price
        AS market_value_local,

    ps.position
        * lp.close_price
        * lf.rate_to_krw
        AS market_value_krw

    ,
    (
        lp.close_price - ps.average_buy_price
    )
    * ps.position
    AS unrealized_pnl_local,

    (
        lp.close_price - ps.average_buy_price
    )
    * ps.position
    * lf.rate_to_krw

AS unrealized_pnl_krw
FROM position_summary ps

CROSS JOIN valuation_date vd

LEFT JOIN latest_price lp
    ON ps.asset_id = lp.asset_id

LEFT JOIN latest_fx lf
    ON ps.currency = lf.currency;