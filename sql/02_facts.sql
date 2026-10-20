-- Facts: daily tokens per model, and each model's list price for each month.

CREATE TABLE fct_model_day AS
SELECT CAST(date AS DATE) AS date, model_permaslug, tokens
FROM stg_rank_day;

-- Price per model per month, from the model-list snapshot closest to mid-month that lists the model.
-- Match order: the exact slug, then the slug without its :variant. A :free variant with no listing is priced 0.
CREATE TABLE fct_price_month AS
WITH months AS (SELECT DISTINCT month FROM dim_date),
models AS (SELECT model_permaslug, base_slug, is_free_variant FROM dim_model WHERE model_permaslug <> 'other'),
cand AS (
    SELECT mo.month, md.model_permaslug, s.snapshot_date, s.id, s.prompt_price, s.completion_price,
           CASE WHEN s.match_key = md.model_permaslug THEN 'exact' ELSE 'base' END AS price_match,
           abs(date_diff('day', CAST(s.snapshot_date AS DATE), mo.month + INTERVAL 14 DAY)) AS dist
    FROM months mo
    CROSS JOIN models md
    JOIN stg_models s ON s.match_key IN (md.model_permaslug, md.base_slug)
    WHERE s.prompt_price IS NOT NULL AND s.completion_price IS NOT NULL
),
best AS (
    SELECT * FROM cand
    QUALIFY row_number() OVER (PARTITION BY month, model_permaslug
                               ORDER BY (price_match = 'exact') DESC, dist, snapshot_date DESC, id) = 1
),
grid AS (SELECT mo.month, md.model_permaslug, md.is_free_variant FROM months mo CROSS JOIN models md)
SELECT
    g.month, g.model_permaslug,
    CASE WHEN b.model_permaslug IS NULL AND g.is_free_variant THEN 0 ELSE b.prompt_price END AS prompt_price,
    CASE WHEN b.model_permaslug IS NULL AND g.is_free_variant THEN 0 ELSE b.completion_price END AS completion_price,
    CAST(b.snapshot_date AS DATE) AS price_snapshot_date,
    CASE WHEN b.model_permaslug IS NOT NULL THEN b.price_match
         WHEN g.is_free_variant THEN 'free_variant' ELSE 'none' END AS price_match
FROM grid g
LEFT JOIN best b USING (month, model_permaslug);

ALTER TABLE fct_price_month ADD COLUMN blended_price_per_m DOUBLE;
ALTER TABLE fct_price_month ADD COLUMN blended_price_per_m_3to1 DOUBLE;
UPDATE fct_price_month SET
    blended_price_per_m = 1e6 * ((SELECT input_weight FROM params) * prompt_price
                               + (1 - (SELECT input_weight FROM params)) * completion_price),
    blended_price_per_m_3to1 = 1e6 * ((SELECT input_weight_alt FROM params) * prompt_price
                                    + (1 - (SELECT input_weight_alt FROM params)) * completion_price);
