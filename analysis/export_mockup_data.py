"""Export the verified numbers the mockup draws, as one JSON file (mockup/data.json)."""

import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
con = duckdb.connect(str(ROOT / "data" / "model.duckdb"), read_only=True)
rows = lambda sql: [dict(zip([c[0] for c in con.description], r)) for r in con.execute(sql).fetchall()]
GROUP = """CASE WHEN country_group IN ('China', 'US') THEN country_group
                WHEN country_group IN ('Europe', 'Rest of world') THEN 'Other named'
                ELSE 'Unattributed' END"""
D = {}
D["as_of"] = "2026-10-19"
D["weekly_share"] = rows(f"""
WITH w AS (SELECT d.week_start, {GROUP} AS g, sum(f.tokens) AS t
           FROM fct_model_day f JOIN dim_date d USING (date) JOIN dim_model m USING (model_permaslug) JOIN dim_lab l USING (org_name)
           GROUP BY 1, 2)
SELECT strftime(week_start, '%Y-%m-%d') AS week, g, t / sum(t) OVER (PARTITION BY week_start) AS share
FROM w ORDER BY 1, 2""")
D["monthly_volume"] = rows("""SELECT strftime(month, '%Y-%m') AS month, sum(tokens) / 1e12 AS tokens_t,
       sum(avg_tokens_per_day) / 1e12 AS per_day_t, month = DATE '2026-10-01' AS partial
FROM mart_lab_month GROUP BY month ORDER BY month""")
D["hhi"] = rows("SELECT strftime(month, '%Y-%m') AS month, hhi_lab, month = DATE '2026-10-01' AS partial FROM mart_concentration_month ORDER BY 1")
D["kpi"] = rows("""SELECT
  (SELECT sum(tokens) / 1e12 FROM mart_lab_month WHERE month = DATE '2026-09-01') AS tokens_sep,
  (SELECT sum(tokens) / 1e12 FROM mart_lab_month WHERE month = DATE '2025-01-01') AS tokens_jan25,
  (SELECT sum(token_share) FROM mart_lab_month WHERE month = DATE '2026-09-01' AND country_group = 'China') AS china_sep,
  (SELECT sum(token_share) FROM mart_lab_month WHERE month = DATE '2025-01-01' AND country_group = 'China') AS china_jan25,
  (SELECT sum(token_share) FROM mart_lab_month WHERE month = DATE '2026-09-01' AND country_group = 'US') AS us_sep,
  (SELECT sum(token_share) FROM mart_lab_month WHERE month = DATE '2025-01-01' AND country_group = 'US') AS us_jan25,
  (SELECT hhi_lab FROM mart_concentration_month WHERE month = DATE '2026-09-01') AS hhi_sep,
  (SELECT hhi_lab FROM mart_concentration_month WHERE month = DATE '2025-01-01') AS hhi_jan25""")[0]
D["group_tokens_vs_spend"] = rows(f"""SELECT {GROUP} AS g, sum(token_share) AS tok, sum(spend_share) AS spend, sum(spend_share_3to1) AS spend31
FROM mart_lab_month WHERE month = DATE '2026-09-01' GROUP BY 1 ORDER BY 1""")
D["lab_tokens_vs_spend"] = rows("""SELECT org_name AS lab, country_group AS cg, token_share AS tok, spend_share AS spend,
       est_spend_usd / nullif(priced_tokens, 0) * 1e6 AS price
FROM mart_lab_month WHERE month = DATE '2026-09-01' AND spend_share IS NOT NULL ORDER BY spend_share DESC LIMIT 10""")
D["china_gap"] = rows("""SELECT strftime(month, '%Y-%m') AS month,
  sum(token_share) FILTER (WHERE country_group = 'China') AS tok, sum(spend_share) FILTER (WHERE country_group = 'China') AS spend
FROM mart_lab_month WHERE month <= DATE '2026-09-01' GROUP BY month ORDER BY month""")
TIER = """CASE WHEN p.blended_price_per_m = 0 THEN 'Free' WHEN p.blended_price_per_m < 0.25 THEN 'Under $0.25'
               WHEN p.blended_price_per_m < 1 THEN '$0.25-1' WHEN p.blended_price_per_m < 5 THEN '$1-5' ELSE '$5+' END"""
D["tiers"] = rows(f"""WITH x AS (SELECT {TIER} AS tier, mm.tokens, mm.tokens * p.blended_price_per_m / 1e6 AS spend
  FROM mart_model_month mm JOIN fct_price_month p USING (month, model_permaslug)
  WHERE p.blended_price_per_m IS NOT NULL AND p.month = DATE '2026-09-01')
SELECT tier, sum(tokens) / (SELECT sum(tokens) FROM x) AS tok, sum(spend) / (SELECT sum(spend) FROM x) AS spend FROM x GROUP BY 1""")
D["price_index"] = rows("""
WITH p AS (SELECT mm.month, mm.model_permaslug, mm.tokens, fp.blended_price_per_m AS price
           FROM mart_model_month mm JOIN fct_price_month fp USING (month, model_permaslug) WHERE fp.blended_price_per_m IS NOT NULL),
avgp AS (SELECT month, sum(tokens * price) / sum(tokens) AS avg_price FROM p GROUP BY 1),
link AS (SELECT cur.month, sum(prev.tokens * cur.price) / sum(prev.tokens * prev.price) AS rel
         FROM p cur JOIN p prev ON prev.model_permaslug = cur.model_permaslug AND prev.month = cur.month - INTERVAL 1 MONTH
         WHERE prev.price > 0 GROUP BY 1),
chain AS (SELECT month, exp(sum(ln(rel)) OVER (ORDER BY month)) AS idx FROM link)
SELECT strftime(a.month, '%Y-%m') AS month, a.avg_price, a.avg_price / first_value(a.avg_price) OVER (ORDER BY a.month) AS avg_idx,
       coalesce(c.idx, 1) AS same_model_idx
FROM avgp a LEFT JOIN chain c USING (month) WHERE a.month <= DATE '2026-09-01' ORDER BY a.month""")
# Lab comes from the sourced lookup by slug prefix, so benchmarked models with no usage still get a lab.
D["scatter"] = rows("""SELECT q.display_name AS name, coalesce(r.org_name, 'Unknown') AS lab,
       CASE r.hq_country WHEN 'China' THEN 'China' WHEN 'United States' THEN 'US' ELSE 'Other' END AS g,
       q.intelligence_index AS iq, q.blended_price_per_m AS price, q.token_share_90d AS share
FROM mart_quality_price_90d q LEFT JOIN ref_labs r ON r.prefix = split_part(q.model_permaslug, '/', 1)
WHERE q.intelligence_index IS NOT NULL AND q.blended_price_per_m > 0""")
D["h6"] = rows("""WITH q AS (SELECT * FROM mart_quality_price_90d WHERE intelligence_index IS NOT NULL),
u AS (SELECT * FROM q WHERE tokens_90d > 0),
fr AS (SELECT a.* FROM q a WHERE a.blended_price_per_m IS NOT NULL AND NOT EXISTS (SELECT 1 FROM q b
       WHERE b.blended_price_per_m <= a.blended_price_per_m AND b.intelligence_index >= a.intelligence_index
       AND (b.blended_price_per_m < a.blended_price_per_m OR b.intelligence_index > a.intelligence_index)))
SELECT (SELECT corr(ri, rt) FROM (SELECT rank() OVER (ORDER BY intelligence_index) ri, rank() OVER (ORDER BY tokens_90d) rt FROM u)) AS spearman,
       (SELECT sum(token_share_90d) FROM (SELECT token_share_90d FROM q ORDER BY intelligence_index DESC LIMIT 5)) AS top5_scorers,
       (SELECT sum(token_share_90d) FROM (SELECT token_share_90d FROM q ORDER BY tokens_90d DESC LIMIT 5)) AS top5_used,
       (SELECT count(*) FROM fr) AS frontier_n, (SELECT count(*) FROM q WHERE blended_price_per_m IS NOT NULL) AS scored_n,
       (SELECT sum(tokens_90d) FROM fr) / (SELECT sum(tokens_90d) FROM q WHERE blended_price_per_m IS NOT NULL) AS frontier_share,  -- as in FINDINGS
       (SELECT count(*) FROM u) AS used_n,
       (SELECT min(intelligence_index) FROM (SELECT intelligence_index FROM q ORDER BY intelligence_index DESC LIMIT 5)) AS scorers_min,
       (SELECT max(intelligence_index) FROM q) AS scorers_max,
       (SELECT min(intelligence_index) FROM (SELECT intelligence_index FROM q ORDER BY tokens_90d DESC LIMIT 5)) AS used_min,
       (SELECT max(intelligence_index) FROM (SELECT intelligence_index FROM q ORDER BY tokens_90d DESC LIMIT 5)) AS used_max""")[0]
D["frontier"] = rows("""WITH q AS (SELECT * FROM mart_quality_price_90d WHERE intelligence_index IS NOT NULL AND blended_price_per_m > 0)
SELECT a.display_name AS name, a.blended_price_per_m AS price, a.intelligence_index AS iq FROM q a WHERE NOT EXISTS (SELECT 1 FROM q b
  WHERE b.blended_price_per_m <= a.blended_price_per_m AND b.intelligence_index >= a.intelligence_index
  AND (b.blended_price_per_m < a.blended_price_per_m OR b.intelligence_index > a.intelligence_index)) ORDER BY price""")
CUTS = {"as measured": ("country_group = 'China'", "country_group = 'US'", "TRUE"),
        "all stealth + long tail credited to the US": ("country_group = 'China'", "country_group IN ('US','Stealth','Long tail')", "TRUE"),
        "paid tokens only": ("country_group = 'China'", "country_group = 'US'", "NOT is_free_variant"),
        "without DeepSeek": ("country_group = 'China'", "country_group = 'US'", "org_name <> 'DeepSeek'")}
D["robustness"] = []
for cut, (c, u, base) in CUTS.items():
    for mo in ("2026-03-01", "2026-06-01", "2026-09-01"):
        r = rows(f"""SELECT sum(f.tokens) FILTER (WHERE {c} AND {base}) / sum(f.tokens) FILTER (WHERE {base}) AS china,
                            sum(f.tokens) FILTER (WHERE {u} AND {base}) / sum(f.tokens) FILTER (WHERE {base}) AS us
                     FROM fct_model_day f JOIN dim_date d USING (date) JOIN dim_model m USING (model_permaslug) JOIN dim_lab l USING (org_name)
                     WHERE d.month = DATE '{mo}'""")[0]
        D["robustness"].append({"cut": cut, "month": mo[:7], **r})
import csv
req = list(csv.DictReader(open(ROOT / "docs/spotcheck/market_share_requests_week_2026-10-12.csv")))
CN, USA = {"DeepSeek", "Z.ai", "Qwen", "Xiaomi"}, {"Google", "OpenAI", "Anthropic", "Meta Llama"}
pct = lambda x: float(x.strip("%")) / 100
D["requests_week"] = {"china": sum(pct(r["share_of_requests"]) for r in req if r["author"] in CN),
                      "us": sum(pct(r["share_of_requests"]) for r in req if r["author"] in USA), "week": "2026-10-12"}
D["launch_split"] = rows("""
WITH f AS (SELECT * FROM mart_launch_weekly WHERE org_name <> 'Stealth (unnamed lab)'
           AND launch_date <= (SELECT max(date) FROM fct_model_day) - INTERVAL 91 DAY),
pk AS (SELECT model_family, any_value(org_name) AS org, any_value(country_group) cg, any_value(launch_date) AS ld, max(avg_daily_share) AS peak,
              arg_max(weeks_since_launch, avg_daily_share) AS pw,
              max(avg_daily_share) FILTER (WHERE weeks_since_launch = 12) w12 FROM f GROUP BY 1 HAVING max(avg_daily_share) >= 0.01),
labday AS (SELECT f.date, m.org_name, sum(f.tokens) / any_value(t.dt) AS s FROM fct_model_day f JOIN dim_model m USING (model_permaslug)
           JOIN (SELECT date, sum(tokens) AS dt FROM fct_model_day GROUP BY 1) t USING (date) GROUP BY 1, 2),
labw AS (SELECT pk.model_family, date_diff('day', pk.ld, l.date) // 7 AS w, avg(l.s) AS s
         FROM pk JOIN labday l ON l.org_name = pk.org AND l.date BETWEEN pk.ld AND pk.ld + INTERVAL 181 DAY GROUP BY 1, 2),
r AS (SELECT pk.*, l0.s AS base, coalesce(l12.s, 0) AS lab12 FROM pk
      JOIN labw l0 ON l0.model_family = pk.model_family AND l0.w = pk.pw
      LEFT JOIN labw l12 ON l12.model_family = pk.model_family AND l12.w = 12)
SELECT coalesce(cg, 'All') AS cut, count(*) AS n, median(w12 / peak) AS model_w12, median(lab12 / base) AS lab_w12
FROM r WHERE cg IN ('US', 'China') OR cg IS NOT NULL GROUP BY ROLLUP(cg)""")
D["china_labs"] = rows("""SELECT org_name AS lab, strftime(month, '%Y-%m') AS month, token_share AS share
FROM mart_lab_month WHERE country_group = 'China' AND month <= DATE '2026-09-01'
  AND org_name IN (SELECT org_name FROM mart_lab_month WHERE month = DATE '2026-09-01' AND country_group = 'China'
                   ORDER BY token_share DESC LIMIT 6) ORDER BY 1, 2""")
D["launch"] = rows("""
WITH f AS (SELECT * FROM mart_launch_weekly WHERE org_name <> 'Stealth (unnamed lab)'
           AND launch_date <= (SELECT max(date) FROM fct_model_day) - INTERVAL 91 DAY),
pk AS (SELECT model_family, any_value(org_name) AS org, any_value(launch_date) AS ld, max(avg_daily_share) AS peak,
              arg_max(weeks_since_launch, avg_daily_share) AS pw FROM f GROUP BY 1 HAVING max(avg_daily_share) >= 0.01),
labday AS (SELECT f.date, m.org_name, sum(f.tokens) / any_value(t.dt) AS s
           FROM fct_model_day f JOIN dim_model m USING (model_permaslug)
           JOIN (SELECT date, sum(tokens) AS dt FROM fct_model_day GROUP BY 1) t USING (date) GROUP BY 1, 2),
labw AS (SELECT pk.model_family, date_diff('day', pk.ld, l.date) // 7 AS w, avg(l.s) AS s
         FROM pk JOIN labday l ON l.org_name = pk.org AND l.date BETWEEN pk.ld AND pk.ld + INTERVAL 181 DAY GROUP BY 1, 2),
labw0 AS (SELECT lw.model_family, lw.s AS base FROM labw lw JOIN pk ON pk.model_family = lw.model_family AND lw.w = pk.pw)
SELECT f.weeks_since_launch AS w, median(f.avg_daily_share / pk.peak) AS model_vs_peak,
       median(coalesce(lw.s, 0) / l0.base) AS lab_vs_base, count(*) AS n   -- a lab gone from the top 50 counts as 0
FROM f JOIN pk USING (model_family) JOIN labw0 l0 ON l0.model_family = f.model_family
LEFT JOIN labw lw ON lw.model_family = f.model_family AND lw.w = f.weeks_since_launch
WHERE f.weeks_since_launch <= 12 GROUP BY 1 ORDER BY 1""")
D["categories"] = rows("""SELECT strftime(month, '%Y-%m') AS month, category, sum(tokens) / sum(sum(tokens)) OVER (PARTITION BY month) AS share
FROM mart_category_month GROUP BY month, category ORDER BY 1, 2""")
D["apps"] = rows("""SELECT app_name AS app, share_of_month_tokens AS share FROM mart_app_month WHERE month = DATE '2026-09-01' ORDER BY tokens DESC LIMIT 10""")
for r in D["launch"] + D["launch_split"]:
    r["n"] = int(r["n"])
for k in ("frontier_n", "scored_n", "used_n"):
    D["h6"][k] = int(D["h6"][k])
(ROOT / "mockup" / "data.json").write_text(json.dumps(D, default=float))
print({k: (len(v) if isinstance(v, list) else v) for k, v in D.items()})
print(D["launch"][:3], D["launch"][12])
