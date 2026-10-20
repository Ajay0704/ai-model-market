"""Step 4, H3-H6: price tiers and price-vs-mix, launch curves, concentration, quality vs usage."""

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
con = duckdb.connect(str(ROOT / "data" / "model.duckdb"), read_only=True)
show = lambda title, sql: print(f"\n## {title}\n" + con.execute(sql).df().to_string(index=False))

TIER = """CASE WHEN {p} = 0 THEN '0 free' WHEN {p} < 0.25 THEN '1 under $0.25' WHEN {p} < 1 THEN '2 $0.25-1'
               WHEN {p} < 5 THEN '3 $1-5' ELSE '4 $5+' END"""

for blend, col in (("15:1", "blended_price_per_m"), ("3:1", "blended_price_per_m_3to1")):
    show(f"H3 price tiers ({blend} blend): share of priced tokens vs share of spend (%)", f"""
    WITH x AS (SELECT p.month, {TIER.format(p='p.' + col)} AS tier, mm.tokens, mm.tokens * p.{col} / 1e6 AS spend
               FROM mart_model_month mm JOIN fct_price_month p USING (month, model_permaslug)
               WHERE p.{col} IS NOT NULL AND p.month IN (DATE '2025-01-01', DATE '2026-01-01', DATE '2026-09-01'))
    , g AS (SELECT month AS mo, tier, sum(tokens) AS t, sum(spend) AS s FROM x GROUP BY 1, 2)
    SELECT strftime(mo, '%Y-%m') AS month, tier,
           round(100 * t / sum(t) OVER (PARTITION BY mo), 1) AS token_pct,
           round(100 * s / sum(s) OVER (PARTITION BY mo), 1) AS spend_pct
    FROM g ORDER BY mo, tier""")

# Price vs mix: chained Laspeyres index over models priced in both consecutive months
show("H3 price vs mix: average price paid vs a same-model price index (Jan 2025 = 1.00)", """
WITH p AS (SELECT mm.month, mm.model_permaslug, mm.tokens, fp.blended_price_per_m AS price
           FROM mart_model_month mm JOIN fct_price_month fp USING (month, model_permaslug) WHERE fp.blended_price_per_m IS NOT NULL),
avgp AS (SELECT month, sum(tokens * price) / sum(tokens) AS avg_price FROM p GROUP BY 1),
link AS (
  SELECT cur.month, sum(prev.tokens * cur.price) / sum(prev.tokens * prev.price) AS rel,
         sum(prev.tokens) AS basket_tokens
  FROM p cur JOIN p prev ON prev.model_permaslug = cur.model_permaslug AND prev.month = cur.month - INTERVAL 1 MONTH
  WHERE prev.price > 0 GROUP BY 1),
chain AS (SELECT month, exp(sum(ln(rel)) OVER (ORDER BY month)) AS price_index FROM link)
SELECT strftime(a.month, '%Y-%m') AS month, round(a.avg_price, 3) AS avg_price_paid,
       round(a.avg_price / first_value(a.avg_price) OVER (ORDER BY a.month), 2) AS avg_price_vs_jan25,
       round(coalesce(c.price_index, 1), 2) AS same_model_price_index
FROM avgp a LEFT JOIN chain c USING (month) ORDER BY a.month""")

# H4: launch curves for launches that mattered (peak >= 1% of daily tokens) with 12+ weeks observed
show("H4 launch curves: retention of peak share, launches peaking at >= 1% of daily tokens", """
WITH f AS (
  SELECT model_family, org_name, country_group, launch_date, weeks_since_launch AS w, avg_daily_share AS s
  FROM mart_launch_weekly WHERE launch_date <= (SELECT max(date) FROM fct_model_day) - INTERVAL 91 DAY),
pk AS (SELECT model_family, max(s) AS peak, arg_max(w, s) AS peak_week FROM f GROUP BY 1),
r AS (SELECT f.model_family, any_value(f.country_group) AS cg, any_value(year(f.launch_date)) AS yr,
             any_value(pk.peak) AS peak, any_value(pk.peak_week) AS peak_week,
             max(f.s) FILTER (WHERE f.w = 8) / any_value(pk.peak) AS keep_w8,
             max(f.s) FILTER (WHERE f.w = 12) / any_value(pk.peak) AS keep_w12
      FROM f JOIN pk USING (model_family) GROUP BY 1)
SELECT cut, count(*) AS launches, round(median(peak_week), 1) AS median_peak_week,
       round(100 * median(keep_w8), 0) AS median_pct_of_peak_at_w8,
       round(100 * median(keep_w12), 0) AS median_pct_of_peak_at_w12,
       round(100 * avg(CASE WHEN keep_w12 < 0.5 THEN 1 ELSE 0 END), 0) AS pct_below_half_by_w12
FROM (SELECT 'all' AS cut, * FROM r WHERE peak >= 0.01
      UNION ALL SELECT 'China', * FROM r WHERE peak >= 0.01 AND cg = 'China'
      UNION ALL SELECT 'US', * FROM r WHERE peak >= 0.01 AND cg = 'US'
      UNION ALL SELECT 'launched 2025', * FROM r WHERE peak >= 0.01 AND yr = 2025
      UNION ALL SELECT 'launched 2026', * FROM r WHERE peak >= 0.01 AND yr = 2026
      UNION ALL SELECT 'peak >= 5% only', * FROM r WHERE peak >= 0.05)
GROUP BY cut ORDER BY cut""")

show("H4 the biggest launches (peak >= 5%): peak and what was left at week 12", """
WITH f AS (SELECT * FROM mart_launch_weekly WHERE launch_date <= (SELECT max(date) FROM fct_model_day) - INTERVAL 91 DAY),
pk AS (SELECT model_family, any_value(org_name) AS org, any_value(launch_date) AS launched,
              max(avg_daily_share) AS peak, arg_max(weeks_since_launch, avg_daily_share) AS peak_week,
              max(avg_daily_share) FILTER (WHERE weeks_since_launch = 12) AS w12 FROM f GROUP BY 1)
SELECT model_family, org, launched, round(100 * peak, 1) AS peak_pct, peak_week, round(100 * w12, 1) AS week12_pct
FROM pk WHERE peak >= 0.05 ORDER BY peak DESC""")

# H5: concentration over time
show("H5 concentration by quarter (average of months)", """
SELECT strftime(date_trunc('quarter', month), '%Y') || '-Q' || quarter(month) AS qtr,
       round(avg(hhi_lab)) AS hhi_lab, round(avg(hhi_family)) AS hhi_family,
       round(100 * avg(top5_family_share), 1) AS top5_family_pct, round(100 * avg(top3_lab_share_named), 1) AS top3_lab_pct_named
FROM mart_concentration_month GROUP BY 1 ORDER BY 1""")

show("H5 cut: lab HHI with stealth counted as one more lab", """
WITH lab AS (SELECT mm.month, m.org_name, sum(mm.tokens) AS t FROM mart_model_month mm JOIN dim_model m USING (model_permaslug)
             WHERE mm.model_permaslug <> 'other' GROUP BY 1, 2),
s AS (SELECT month, t / sum(t) OVER (PARTITION BY month) AS sh FROM lab)
SELECT strftime(month, '%Y-%m') AS month, round(10000 * sum(sh * sh)) AS hhi_lab_incl_stealth FROM s
WHERE month IN (DATE '2025-01-01', DATE '2025-07-01', DATE '2026-01-01', DATE '2026-06-01', DATE '2026-09-01') GROUP BY 1 ORDER BY 1""")

# H6: quality vs usage, last 90 days
show("H6: do higher-scoring models get more use? (Artificial Analysis models with any 90-day usage)", """
WITH q AS (SELECT * FROM mart_quality_price_90d WHERE intelligence_index IS NOT NULL AND tokens_90d > 0)
SELECT count(*) AS models,
  round(corr(rank_int, rank_tok), 2) AS spearman_intelligence_vs_tokens,
  round(corr(rank_price, rank_tok), 2) AS spearman_price_vs_tokens,
  round(corr(rank_int, rank_price), 2) AS spearman_intelligence_vs_price
FROM (SELECT *, rank() OVER (ORDER BY intelligence_index) AS rank_int, rank() OVER (ORDER BY tokens_90d) AS rank_tok,
             rank() OVER (ORDER BY blended_price_per_m) AS rank_price FROM q)""")

show("H6: top 5 by intelligence vs top 5 by usage (last 90 days)", """
WITH q AS (SELECT * FROM mart_quality_price_90d WHERE intelligence_index IS NOT NULL)
(SELECT 'top 5 by intelligence' AS list, display_name, org_name, intelligence_index AS iq, round(blended_price_per_m, 2) AS usd_per_m,
        round(100 * token_share_90d, 2) AS share_90d_pct FROM q ORDER BY intelligence_index DESC LIMIT 5)
UNION ALL
(SELECT 'top 5 by usage', display_name, org_name, intelligence_index, round(blended_price_per_m, 2),
        round(100 * token_share_90d, 2) FROM q ORDER BY tokens_90d DESC LIMIT 5)""")

for blend, col in (("15:1", "blended_price_per_m"), ("3:1", "blended_price_per_m_3to1")):
    show(f"H6 price-quality frontier ({blend}): models no other model beats on both price and score", f"""
    WITH q AS (SELECT * FROM mart_quality_price_90d WHERE intelligence_index IS NOT NULL AND {col} IS NOT NULL),
    fr AS (SELECT a.* FROM q a WHERE NOT EXISTS (
             SELECT 1 FROM q b WHERE b.{col} <= a.{col} AND b.intelligence_index >= a.intelligence_index
               AND (b.{col} < a.{col} OR b.intelligence_index > a.intelligence_index)))
    SELECT (SELECT count(*) FROM fr) AS frontier_models, (SELECT count(*) FROM q) AS scored_models,
           round(100 * (SELECT sum(tokens_90d) FROM fr) / (SELECT sum(tokens_90d) FROM q), 1) AS frontier_pct_of_scored_usage,
           (SELECT string_agg(display_name || ' ($' || round({col}, 2) || ', ' || intelligence_index || ')', '; ' ORDER BY {col}) FROM fr) AS frontier""")
