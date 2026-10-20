-- Marts: the tables the dashboards read. Metric definitions live in docs/METRICS.md.

-- Days with data per month (the API skipped 2 days), used for "average tokens per day".
CREATE TABLE month_days AS
SELECT month, count(*) FILTER (WHERE NOT is_missing_day) AS data_days FROM dim_date GROUP BY 1;

CREATE TABLE month_totals AS
SELECT d.month, sum(f.tokens) AS month_tokens
FROM fct_model_day f JOIN dim_date d USING (date) GROUP BY 1;

-- Model x month: tokens, share of all tokens, estimated spend at that month's list price.
CREATE TABLE mart_model_month AS
SELECT
    d.month, f.model_permaslug,
    sum(f.tokens) AS tokens,
    count(*) AS days_in_top50,
    sum(f.tokens) / any_value(md.data_days) AS avg_tokens_per_day,
    sum(f.tokens) / any_value(mt.month_tokens) AS token_share,
    any_value(p.blended_price_per_m) AS blended_price_per_m,
    sum(f.tokens) * any_value(p.blended_price_per_m) / 1e6 AS est_spend_usd,
    sum(f.tokens) * any_value(p.blended_price_per_m_3to1) / 1e6 AS est_spend_usd_3to1,
    any_value(p.price_match) AS price_match
FROM fct_model_day f
JOIN dim_date d USING (date)
JOIN month_days md USING (month)
JOIN month_totals mt USING (month)
LEFT JOIN fct_price_month p ON p.month = d.month AND p.model_permaslug = f.model_permaslug
GROUP BY 1, 2;

-- Organization x month. Spend share is over priced tokens only (the long tail and stealth models have no price).
CREATE TABLE mart_lab_month AS
WITH x AS (
    SELECT mm.month, m.org_name, l.country_group, l.hq_country,
           sum(mm.tokens) AS tokens,
           sum(mm.avg_tokens_per_day) AS avg_tokens_per_day,
           sum(mm.token_share) AS token_share,
           sum(mm.est_spend_usd) AS est_spend_usd,
           sum(mm.est_spend_usd_3to1) AS est_spend_usd_3to1,
           sum(mm.tokens) FILTER (WHERE m.open_weights) AS open_weight_tokens,
           sum(mm.tokens) FILTER (WHERE m.is_free_variant) AS free_variant_tokens,
           sum(mm.tokens) FILTER (WHERE mm.est_spend_usd IS NOT NULL) AS priced_tokens
    FROM mart_model_month mm
    JOIN dim_model m USING (model_permaslug)
    JOIN dim_lab l USING (org_name)
    GROUP BY 1, 2, 3, 4
)
SELECT *,
    est_spend_usd / sum(est_spend_usd) OVER (PARTITION BY month) AS spend_share,
    est_spend_usd_3to1 / sum(est_spend_usd_3to1) OVER (PARTITION BY month) AS spend_share_3to1
FROM x;

-- Concentration per month. HHI is computed on named tokens only (the 'other' row is many models, not one).
CREATE TABLE mart_concentration_month AS
WITH fam AS (
    SELECT mm.month, m.model_family, m.org_name, sum(mm.tokens) AS tokens
    FROM mart_model_month mm JOIN dim_model m USING (model_permaslug)
    WHERE mm.model_permaslug <> 'other' GROUP BY 1, 2, 3
),
fam_s AS (
    SELECT *, tokens / sum(tokens) OVER (PARTITION BY month) AS s_named,
           row_number() OVER (PARTITION BY month ORDER BY tokens DESC) AS rk
    FROM fam
),
lab AS (
    SELECT month, org_name, sum(tokens) AS tokens FROM fam
    WHERE org_name NOT IN ('Stealth (unnamed lab)', 'Pending lookup') GROUP BY 1, 2
),
lab_s AS (
    SELECT *, tokens / sum(tokens) OVER (PARTITION BY month) AS s_named,
           row_number() OVER (PARTITION BY month ORDER BY tokens DESC) AS rk
    FROM lab
)
SELECT f.month,
    10000 * sum(f.s_named * f.s_named) AS hhi_family,
    any_value(l.hhi_lab) AS hhi_lab,
    sum(f.tokens) FILTER (WHERE f.rk = 1) / any_value(mt.month_tokens) AS top1_family_share,
    sum(f.tokens) FILTER (WHERE f.rk <= 5) / any_value(mt.month_tokens) AS top5_family_share,
    any_value(l.top3_lab_share_named) AS top3_lab_share_named,
    count(*) AS families_in_top50,
    1 - sum(f.tokens) / any_value(mt.month_tokens) AS other_share
FROM fam_s f
JOIN month_totals mt USING (month)
LEFT JOIN (SELECT month, 10000 * sum(s_named * s_named) AS hhi_lab,
             sum(s_named) FILTER (WHERE rk <= 3) AS top3_lab_share_named
      FROM lab_s GROUP BY 1) l USING (month)
GROUP BY 1;

-- Launch curves: a family's share of each day's tokens, by week since it first entered the top 50.
-- Only families first seen on or after 2025-02-01, so a "launch" is a real entry, not the window's start.
CREATE TABLE mart_launch_weekly AS
WITH day_tot AS (SELECT date, sum(tokens) AS day_tokens FROM fct_model_day GROUP BY 1),
fam_day AS (
    SELECT f.date, m.model_family, any_value(m.org_name) AS org_name, sum(f.tokens) AS tokens
    FROM fct_model_day f JOIN dim_model m USING (model_permaslug)
    WHERE f.model_permaslug <> 'other' GROUP BY 1, 2
),
launch AS (
    SELECT model_family, any_value(org_name) AS org_name, min(date) AS launch_date
    FROM fam_day GROUP BY 1 HAVING min(date) >= DATE '2025-02-01'
),
grid AS (
    SELECT l.model_family, l.org_name, l.launch_date, d.date,
           date_diff('day', l.launch_date, d.date) // 7 AS weeks_since_launch
    FROM launch l JOIN dim_date d ON d.date BETWEEN l.launch_date AND l.launch_date + INTERVAL 181 DAY
    WHERE NOT d.is_missing_day
)
SELECT g.model_family, g.org_name, lb.country_group, g.launch_date, g.weeks_since_launch,
    count(*) AS days_observed,
    avg(coalesce(fd.tokens, 0) / dt.day_tokens) AS avg_daily_share
FROM grid g
JOIN day_tot dt USING (date)
LEFT JOIN fam_day fd ON fd.date = g.date AND fd.model_family = g.model_family
JOIN dim_lab lb ON lb.org_name = g.org_name
GROUP BY 1, 2, 3, 4, 5;

-- Quality vs price vs usage, last 90 days of data. Usage counts the model and its :variants together.
CREATE TABLE mart_quality_price_90d AS
WITH win AS (SELECT max(date) - INTERVAL 89 DAY AS d0, max(date) AS d1 FROM fct_model_day),
use AS (
    SELECT m.base_slug, sum(f.tokens) AS tokens_90d
    FROM fct_model_day f JOIN dim_model m USING (model_permaslug), win
    WHERE f.date BETWEEN win.d0 AND win.d1 AND f.model_permaslug <> 'other'
    GROUP BY 1
),
tot AS (SELECT sum(tokens) AS all_90d FROM fct_model_day, win WHERE date BETWEEN win.d0 AND win.d1)
SELECT b.model_permaslug, b.display_name,
    coalesce(m.org_name, 'Pending lookup') AS org_name, l.country_group, m.open_weights,
    b.intelligence_index, b.coding_index, b.agentic_index,
    1e6 * ((SELECT input_weight FROM params) * b.prompt_price + (1 - (SELECT input_weight FROM params)) * b.completion_price) AS blended_price_per_m,
    1e6 * ((SELECT input_weight_alt FROM params) * b.prompt_price + (1 - (SELECT input_weight_alt FROM params)) * b.completion_price) AS blended_price_per_m_3to1,
    coalesce(u.tokens_90d, 0) AS tokens_90d,
    coalesce(u.tokens_90d, 0) / (SELECT all_90d FROM tot) AS token_share_90d,
    b.as_of AS benchmark_as_of
FROM stg_bench_aa b
LEFT JOIN use u ON u.base_slug = split_part(b.model_permaslug, ':', 1)
LEFT JOIN (SELECT DISTINCT base_slug, org_name, open_weights FROM dim_model WHERE variant = '') m
       ON m.base_slug = split_part(b.model_permaslug, ':', 1)
LEFT JOIN dim_lab l ON l.org_name = coalesce(m.org_name, 'Pending lookup');

-- Task category x organization x month (sampled estimates from OpenRouter; use as mix shares, not totals).
CREATE TABLE mart_category_month AS
WITH c AS (
    SELECT CAST(c.month AS DATE) AS month, c.category,
        CASE WHEN c.model_permaslug = 'other' THEN 'Long tail (outside top 50)'
             WHEN split_part(c.model_permaslug, '/', 1) IN ('stealth', 'openrouter') THEN 'Stealth (unnamed lab)'
             ELSE coalesce(r.org_name, 'Pending lookup') END AS org_name,
        c.tokens
    FROM stg_category_month c
    LEFT JOIN ref_labs r ON r.prefix = split_part(c.model_permaslug, '/', 1)
)
SELECT c.month, c.category, c.org_name, l.country_group, sum(c.tokens) AS tokens,
    sum(c.tokens) / sum(sum(c.tokens)) OVER (PARTITION BY c.month, c.category) AS share_in_category
FROM c JOIN dim_lab l USING (org_name)
GROUP BY 1, 2, 3, 4;

-- Top 100 apps per month.
CREATE TABLE mart_app_month AS
SELECT CAST(a.month AS DATE) AS month, a.rank, a.app_id, a.app_name, a.tokens, a.requests,
    a.tokens / nullif(a.requests, 0) AS tokens_per_request,
    a.tokens / mt.month_tokens AS share_of_month_tokens
FROM stg_app_month a JOIN month_totals mt ON mt.month = CAST(a.month AS DATE);

CREATE TABLE mart_task_snapshot AS SELECT * FROM stg_task_snapshot;

-- One flat table for Tableau (the Olist Tableau build also used flattened tables).
CREATE TABLE tableau_model_day AS
SELECT f.date, d.month, d.week_start, f.model_permaslug, m.model_family, m.display_name,
    m.org_name, l.country_group, l.hq_country, l.org_type, m.open_weights, m.is_free_variant, m.is_stealth,
    f.tokens,
    sum(f.tokens) OVER (PARTITION BY f.date) AS day_tokens,
    f.tokens * p.blended_price_per_m / 1e6 AS est_spend_usd
FROM fct_model_day f
JOIN dim_date d USING (date)
JOIN dim_model m USING (model_permaslug)
JOIN dim_lab l USING (org_name)
LEFT JOIN fct_price_month p ON p.month = d.month AND p.model_permaslug = f.model_permaslug;
