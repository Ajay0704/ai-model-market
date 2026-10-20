-- Dimensions: date, lab, model.

-- One row per calendar day in the pulled window. The two days the API skipped are flagged, never zero-filled.
CREATE TABLE dim_date AS
WITH bounds AS (SELECT min(CAST(date AS DATE)) AS d0, max(CAST(date AS DATE)) AS d1 FROM stg_rank_day),
days AS (SELECT CAST(unnest(generate_series(d0, d1, INTERVAL 1 DAY)) AS DATE) AS date FROM bounds)
SELECT
    d.date,
    CAST(date_trunc('month', d.date) AS DATE) AS month,
    CAST(date_trunc('week', d.date) AS DATE) AS week_start,           -- Monday
    year(d.date) AS year,
    d.date NOT IN (SELECT CAST(date AS DATE) FROM stg_rank_day) AS is_missing_day
FROM days d;

-- One row per organization. labs.csv maps each slug prefix to its organization (sourced per row);
-- the three synthetic groups below cover tokens no named lab can be credited with.
CREATE TABLE dim_lab AS
WITH sourced AS (  -- several prefixes can share one organization (meta + meta-llama); keep one row per org
    SELECT org_name, hq_country, org_type, source_url, source_type FROM ref_labs
    QUALIFY row_number() OVER (PARTITION BY org_name ORDER BY source_type = 'first_party' DESC, prefix) = 1
),
synthetic AS (
    SELECT * FROM (VALUES
        ('Stealth (unnamed lab)', 'Unknown', 'stealth', 'https://openrouter.ai/rankings', 'first_party'),
        ('Long tail (outside top 50)', 'Unknown', 'long_tail', 'https://openrouter.ai/rankings', 'first_party'),
        ('Pending lookup', 'Unknown', 'pending', NULL, NULL)
    ) t(org_name, hq_country, org_type, source_url, source_type)
)
SELECT
    org_name,
    hq_country,
    CASE
        WHEN org_type IN ('stealth', 'long_tail', 'pending') THEN CASE org_type WHEN 'stealth' THEN 'Stealth'
                                                                    WHEN 'long_tail' THEN 'Long tail' ELSE 'Unknown' END
        WHEN hq_country = 'United States' THEN 'US'
        WHEN hq_country = 'China' THEN 'China'
        WHEN hq_country IN ('France', 'Germany', 'United Kingdom', 'Netherlands', 'Switzerland', 'Sweden',
                            'Finland', 'Spain', 'Italy', 'Ireland', 'Poland', 'Belgium', 'Austria', 'Denmark') THEN 'Europe'
        WHEN hq_country IS NULL OR hq_country = 'Unknown' THEN 'Unknown'
        ELSE 'Rest of world'
    END AS country_group,
    org_type, source_url, source_type
FROM (SELECT * FROM sourced UNION ALL SELECT * FROM synthetic);

-- One row per model slug seen in the daily rankings (plus the 'other' row).
CREATE TABLE dim_model AS
WITH slugs AS (
    SELECT model_permaslug,
           min(CAST(date AS DATE)) AS first_seen_date,
           max(CAST(date AS DATE)) AS last_seen_date,
           count(*) AS days_in_top50
    FROM stg_rank_day GROUP BY 1
),
parsed AS (
    SELECT *,
        split_part(model_permaslug, '/', 1) AS prefix,
        split_part(model_permaslug, ':', 1) AS base_slug,
        CASE WHEN contains(model_permaslug, ':') THEN split_part(model_permaslug, ':', 2) ELSE '' END AS variant
    FROM slugs
),
-- Latest snapshot entry per match key: the newest name, release date, context length and Hugging Face link.
latest AS (
    SELECT match_key, name, created, context_length, has_hf_field, hugging_face_id
    FROM stg_models
    QUALIFY row_number() OVER (PARTITION BY match_key ORDER BY snapshot_date DESC) = 1
),
-- Whether any snapshot ever showed this key with the hugging_face_id field (older snapshots lack the field).
hf AS (
    SELECT match_key, bool_or(has_hf_field) AS ever_has_hf_field,
           max(CASE WHEN coalesce(hugging_face_id, '') <> '' THEN hugging_face_id END) AS hf_id
    FROM stg_models GROUP BY 1
)
SELECT
    p.model_permaslug,
    p.prefix,
    p.base_slug,
    regexp_replace(p.base_slug, '-20[0-9]{6}$', '') AS model_family,
    p.variant,
    p.variant = 'free' AS is_free_variant,
    p.prefix IN ('stealth', 'openrouter') AS is_stealth,
    CASE
        WHEN p.model_permaslug = 'other' THEN 'Long tail (outside top 50)'
        WHEN p.prefix IN ('stealth', 'openrouter') THEN 'Stealth (unnamed lab)'
        ELSE coalesce(l.org_name, 'Pending lookup')
    END AS org_name,
    coalesce(m1.name, m2.name) AS display_name,
    CAST(to_timestamp(coalesce(m1.created, m2.created)) AS DATE) AS listed_date,
    coalesce(m1.context_length, m2.context_length) AS context_length,
    -- Open weights: OpenRouter links the model to a Hugging Face repo. NULL = no snapshot carried the field.
    CASE
        WHEN p.model_permaslug = 'other' OR p.prefix IN ('stealth', 'openrouter') THEN NULL
        WHEN coalesce(h1.hf_id, h2.hf_id) IS NOT NULL THEN TRUE
        WHEN coalesce(h1.ever_has_hf_field, h2.ever_has_hf_field) THEN FALSE
        ELSE NULL
    END AS open_weights,
    coalesce(h1.hf_id, h2.hf_id) AS hugging_face_id,
    p.first_seen_date, p.last_seen_date, p.days_in_top50
FROM parsed p
LEFT JOIN ref_labs l ON l.prefix = p.prefix
LEFT JOIN latest m1 ON m1.match_key = p.model_permaslug
LEFT JOIN latest m2 ON m2.match_key = p.base_slug
LEFT JOIN hf h1 ON h1.match_key = p.model_permaslug
LEFT JOIN hf h2 ON h2.match_key = p.base_slug;
