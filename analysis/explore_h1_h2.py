"""Step 4, H1 and H2: China's share of tokens, and tokens vs spend, tested across cuts."""

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
con = duckdb.connect(str(ROOT / "data" / "model.duckdb"), read_only=True)
show = lambda title, sql: print(f"\n## {title}\n" + con.execute(sql).df().to_string(index=False))

# Base series: monthly token share by country group
show("H1 base: token share by country group (%)", """
PIVOT (SELECT strftime(month, '%Y-%m') AS m, country_group, round(100 * sum(token_share), 1) AS s
       FROM mart_lab_month GROUP BY 1, 2)
ON country_group USING first(s) ORDER BY m""")

# When did China pass the US, by week? And did it stay ahead?
show("H1 weekly crossover: weeks where China > US, by quarter", """
WITH w AS (
  SELECT d.week_start, l.country_group, sum(f.tokens) AS t
  FROM fct_model_day f JOIN dim_date d USING (date) JOIN dim_model m USING (model_permaslug) JOIN dim_lab l USING (org_name)
  GROUP BY 1, 2),
p AS (SELECT week_start, sum(t) FILTER (WHERE country_group = 'China') / sum(t) AS china,
             sum(t) FILTER (WHERE country_group = 'US') / sum(t) AS us FROM w GROUP BY 1)
SELECT strftime(date_trunc('quarter', week_start), '%Y-Q') || quarter(week_start) AS qtr,
       count(*) AS weeks, count(*) FILTER (WHERE china > us) AS china_ahead,
       min(week_start) FILTER (WHERE china > us) AS first_week_ahead
FROM p GROUP BY 1 ORDER BY 1""")

# Robustness cuts for the latest full month and the 2026 trend
show("H1 cuts, Sep 2026 and Mar 2026 (China share vs US share, %)", """
WITH b AS (
  SELECT d.month, l.country_group, m.org_name, m.is_free_variant, f.tokens
  FROM fct_model_day f JOIN dim_date d USING (date) JOIN dim_model m USING (model_permaslug) JOIN dim_lab l USING (org_name)
  WHERE d.month IN (DATE '2026-03-01', DATE '2026-06-01', DATE '2026-09-01')),
cuts AS (
  SELECT month, 'a. as measured' AS cut,
         sum(tokens) FILTER (WHERE country_group = 'China') / sum(tokens) AS china,
         sum(tokens) FILTER (WHERE country_group = 'US') / sum(tokens) AS us FROM b GROUP BY 1
  UNION ALL
  SELECT month, 'b. worst case: all stealth + long tail credited to US',
         sum(tokens) FILTER (WHERE country_group = 'China') / sum(tokens),
         sum(tokens) FILTER (WHERE country_group IN ('US', 'Stealth', 'Long tail')) / sum(tokens) FROM b GROUP BY 1
  UNION ALL
  SELECT month, 'c. paid tokens only (free variants removed)',
         sum(tokens) FILTER (WHERE country_group = 'China' AND NOT is_free_variant) / sum(tokens) FILTER (WHERE NOT is_free_variant),
         sum(tokens) FILTER (WHERE country_group = 'US' AND NOT is_free_variant) / sum(tokens) FILTER (WHERE NOT is_free_variant) FROM b GROUP BY 1
  UNION ALL
  SELECT month, 'd. without the top Chinese lab (DeepSeek)',
         sum(tokens) FILTER (WHERE country_group = 'China' AND org_name <> 'DeepSeek') / sum(tokens) FILTER (WHERE org_name <> 'DeepSeek'),
         sum(tokens) FILTER (WHERE country_group = 'US') / sum(tokens) FILTER (WHERE org_name <> 'DeepSeek') FROM b GROUP BY 1)
SELECT strftime(month, '%Y-%m') AS month, cut, round(100 * china, 1) AS china_pct, round(100 * us, 1) AS us_pct,
       CASE WHEN china > us THEN 'China ahead' ELSE 'US ahead' END AS verdict
FROM cuts ORDER BY month, cut""")

show("H1 breadth: Chinese labs with >= 2% of tokens, by month", """
SELECT strftime(month, '%Y-%m') AS month, count(*) AS chinese_labs_over_2pct,
       string_agg(org_name || ' ' || round(100 * token_share, 1), ', ' ORDER BY token_share DESC) AS labs
FROM mart_lab_month WHERE country_group = 'China' AND token_share >= 0.02
  AND month IN (DATE '2025-01-01', DATE '2025-07-01', DATE '2026-01-01', DATE '2026-06-01', DATE '2026-09-01')
GROUP BY 1 ORDER BY 1""")

show("H1 programming category: China's share of programming tokens (%)", """
SELECT strftime(month, '%Y-%m') AS month, round(100 * sum(share_in_category) FILTER (WHERE country_group = 'China'), 1) AS china,
       round(100 * sum(share_in_category) FILTER (WHERE country_group = 'US'), 1) AS us
FROM mart_category_month WHERE category = 'programming' GROUP BY 1 ORDER BY 1""")

# H2: tokens vs spend, both price blends
show("H2: China and US, token share vs spend share (15:1 and 3:1 blends, %)", """
SELECT strftime(month, '%Y-%m') AS month,
  round(100 * sum(token_share) FILTER (WHERE country_group = 'China'), 1) AS china_tok,
  round(100 * sum(spend_share) FILTER (WHERE country_group = 'China'), 1) AS china_spend,
  round(100 * sum(spend_share_3to1) FILTER (WHERE country_group = 'China'), 1) AS china_spend_3to1,
  round(100 * sum(token_share) FILTER (WHERE country_group = 'US'), 1) AS us_tok,
  round(100 * sum(spend_share) FILTER (WHERE country_group = 'US'), 1) AS us_spend,
  round(100 * sum(spend_share_3to1) FILTER (WHERE country_group = 'US'), 1) AS us_spend_3to1
FROM mart_lab_month GROUP BY 1 ORDER BY 1""")

show("H2 by lab, Sep 2026: token share vs spend share (top 10 by spend, %)", """
SELECT org_name, country_group, round(100 * token_share, 1) AS tok, round(100 * spend_share, 1) AS spend,
       round(100 * spend_share_3to1, 1) AS spend_3to1,
       round(est_spend_usd / nullif(priced_tokens, 0) * 1e6, 3) AS avg_price_per_m
FROM mart_lab_month WHERE month = DATE '2026-09-01' AND spend_share IS NOT NULL
ORDER BY spend_share DESC LIMIT 10""")
