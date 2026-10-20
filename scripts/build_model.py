"""Build the DuckDB model: raw JSON -> staging tables -> sql/*.sql (dims, facts, marts) -> CSVs.

Usage: python scripts/build_model.py
Writes data/model.duckdb (gitignored) and data/processed/*.csv (what Tableau and Power BI read).
Run scripts/check_model.py afterwards; it writes docs/MODEL_CHECKS.md.
"""

import glob
import json
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
REF = ROOT / "data" / "reference"
OUT = ROOT / "data" / "processed"
DB = ROOT / "data" / "model.duckdb"

# Share of input (prompt) tokens used to blend the two list prices into one price per token.
# OpenRouter's 100T-token study (arXiv 2601.10088, section 4.3) reports about 6K prompt vs 400 completion
# tokens per request, so 15:1. Artificial Analysis's 3:1 convention is kept as a sensitivity check.
INPUT_WEIGHT = 15 / 16
INPUT_WEIGHT_ALT = 3 / 4

EXPORT = ["dim_date", "dim_month", "dim_lab", "dim_model", "fct_model_day", "fct_price_month", "mart_model_month",
          "mart_lab_month", "mart_concentration_month", "mart_launch_weekly", "mart_quality_price_90d",
          "mart_category_month", "mart_app_month", "mart_task_snapshot", "tableau_model_day"]


def resp(path):
    return json.load(open(path))["response"]


def num(x):
    return None if x in (None, "") else float(x)


def staging():
    rank = []
    for f in sorted(glob.glob(str(RAW / "rankings_daily" / "*.json"))):
        r = resp(f)
        rank += [{"date": x["date"], "model_permaslug": x["model_permaslug"], "tokens": int(x["total_tokens"]),
                  "as_of": r["meta"]["as_of"]} for x in r["data"]]

    models = []
    snaps = [(Path(f).stem[:8], "wayback", f) for f in sorted(glob.glob(str(RAW / "models_wayback" / "*.json")))]
    snaps += [(Path(f).stem.split("_")[1].replace("-", ""), "live", f) for f in sorted(glob.glob(str(RAW / "models" / "*.json")))]
    for stamp, source, f in snaps:
        for m in resp(f)["data"]:
            mid, canon = m["id"], m.get("canonical_slug")
            # A variant id (x:free, x:batch) shares its base model's canonical slug, so it must only
            # register as canonical:variant. Registering the bare canonical too let a :batch or :free
            # price stand in for the full price (caught by the answer key, 2026-10-19).
            keys = {mid}
            if canon:
                if ":" in mid and ":" not in canon:
                    keys.add(f"{canon}:{mid.split(':', 1)[1]}")
                else:
                    keys.add(canon)
            p = m.get("pricing") or {}
            for k in keys:
                models.append({"snapshot_date": f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}", "source": source,
                               "match_key": k, "id": mid, "canonical_slug": canon, "name": m.get("name"),
                               "created": m.get("created"), "context_length": m.get("context_length"),
                               "has_hf_field": "hugging_face_id" in m, "hugging_face_id": m.get("hugging_face_id"),
                               "prompt_price": num(p.get("prompt")), "completion_price": num(p.get("completion"))})

    cats = []
    for f in sorted(glob.glob(str(RAW / "rankings_category_month" / "*.json"))):
        r = resp(f)
        cat = Path(f).stem.rsplit("_", 2)[0].replace("marketing-seo", "marketing/seo")
        cats += [{"month": x["date"], "category": cat, "model_permaslug": x["model_permaslug"],
                  "tokens": int(x["total_tokens"])} for x in r["data"] if x["date"] >= r["meta"]["start_date"]]

    apps = []
    for f in sorted(glob.glob(str(RAW / "app_rankings_month" / "*.json"))):
        r = resp(f)
        apps += [{"month": r["meta"]["start_date"], "rank": x["rank"], "app_id": x["app_id"], "app_name": x["app_name"],
                  "tokens": int(x["total_tokens"]), "requests": int(x["total_requests"])} for x in r["data"]]

    aa = resp(sorted(glob.glob(str(RAW / "benchmarks" / "artificial-analysis_*.json")))[-1])
    bench = [{"model_permaslug": x["model_permaslug"], "display_name": x["display_name"],
              "intelligence_index": x.get("intelligence_index"), "coding_index": x.get("coding_index"),
              "agentic_index": x.get("agentic_index"), "prompt_price": num((x.get("pricing") or {}).get("prompt")),
              "completion_price": num((x.get("pricing") or {}).get("completion")), "as_of": aa["meta"]["as_of"]}
             for x in aa["data"]]

    t = resp(sorted(glob.glob(str(RAW / "task_classifications" / "*.json")))[-1])["data"]
    tasks = [{"tag": c["tag"], "display_name": c["display_name"], "macro_category": c["macro_category"],
              "usage_share": c["usage_share"], "token_share": c["token_share"], "as_of": t["as_of"]}
             for c in t["classifications"]]

    labs_path = REF / "labs.csv"
    cols = ["prefix", "org_name", "hq_city", "hq_country", "org_type", "source_url", "source_type", "notes"]
    labs = (pd.read_csv(labs_path, dtype=str) if labs_path.exists() else pd.DataFrame(columns=cols)).astype("string")
    return {"stg_rank_day": pd.DataFrame(rank), "stg_models": pd.DataFrame(models),
            "stg_category_month": pd.DataFrame(cats), "stg_app_month": pd.DataFrame(apps),
            "stg_bench_aa": pd.DataFrame(bench), "stg_task_snapshot": pd.DataFrame(tasks), "ref_labs": labs}


def main():
    DB.unlink(missing_ok=True)
    con = duckdb.connect(str(DB))
    for name, df in staging().items():
        con.register(f"_{name}", df)
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM _{name}")
        con.unregister(f"_{name}")
    con.execute(f"CREATE TABLE params AS SELECT {INPUT_WEIGHT} AS input_weight, {INPUT_WEIGHT_ALT} AS input_weight_alt")
    for sql in sorted((ROOT / "sql").glob("*.sql")):
        con.execute(sql.read_text())
        print(f"ran {sql.name}")
    OUT.mkdir(parents=True, exist_ok=True)
    for t in EXPORT:
        n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        con.execute(f"COPY {t} TO '{OUT / (t + '.csv')}' (HEADER, DELIMITER ',')")
        print(f"  {t}: {n} rows")
    con.close()


if __name__ == "__main__":
    main()
