"""Answer key: recompute the headline numbers a second, independent way, then compare with the model.

The key side reads ONLY the raw JSON pulls and data/reference/labs.csv with pandas. It shares no code
and no SQL with build_model.py. The model side queries data/model.duckdb. Every dashboard number must
match the key; a mismatch is a bug in one of them until proven otherwise.

Usage: python scripts/build_model.py && python scripts/answer_key.py
Writes docs/ANSWER_KEY.md; exits 1 on any mismatch.
"""

import datetime as dt
import glob
import json
import re
import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
W_IN = 15 / 16  # same documented assumption as METRICS.md, restated here on purpose
EUROPE = {"France", "Germany", "United Kingdom", "Netherlands", "Switzerland", "Sweden", "Finland", "Spain",
          "Italy", "Ireland", "Poland", "Belgium", "Austria", "Denmark"}
MONTHS = ["2025-01", "2026-01", "2026-09"]


def body(path):
    return json.load(open(path))["response"]


# ---------- key side: pandas from raw files ----------

def load_key():
    rows = []
    for f in glob.glob(str(RAW / "rankings_daily" / "*.json")):
        rows += body(f)["data"]
    d = pd.DataFrame(rows)
    d["tokens"] = d["total_tokens"].astype("int64")
    d["month"] = d["date"].str[:7]
    d["prefix"] = d["model_permaslug"].str.split("/").str[0]
    d["base"] = d["model_permaslug"].str.split(":").str[0]
    d["variant"] = d["model_permaslug"].map(lambda s: s.split(":", 1)[1] if ":" in s else "")
    d["family"] = d["base"].map(lambda s: re.sub(r"-20\d{6}$", "", s))

    labs = pd.read_csv(ROOT / "data" / "reference" / "labs.csv", dtype=str)
    org = dict(zip(labs.prefix, labs.org_name))
    country = dict(zip(labs.org_name, labs.hq_country))

    def org_of(r):
        if r.model_permaslug == "other":
            return "Long tail (outside top 50)"
        if r.prefix in ("stealth", "openrouter"):
            return "Stealth (unnamed lab)"
        return org.get(r.prefix, "MISSING")

    def group_of(o):
        if o == "Long tail (outside top 50)":
            return "Long tail"
        if o == "Stealth (unnamed lab)":
            return "Stealth"
        c = country.get(o)
        if c == "United States":
            return "US"
        if c == "China":
            return "China"
        if c in EUROPE:
            return "Europe"
        if c in (None, "Unknown") or pd.isna(c):
            return "Unknown"
        return "Rest of world"

    d["org"] = d.apply(org_of, axis=1)
    d["group"] = d["org"].map(group_of)

    # Prices and open-weight status from every model-list snapshot
    snaps = []
    for f in sorted(glob.glob(str(RAW / "models_wayback" / "*.json"))):
        snaps.append((dt.date(int(Path(f).stem[:4]), int(Path(f).stem[4:6]), int(Path(f).stem[6:8])), f))
    for f in sorted(glob.glob(str(RAW / "models" / "*.json"))):
        snaps.append((dt.date.fromisoformat(Path(f).stem.split("_")[1]), f))
    by_key = {}
    for sd, f in snaps:
        for m in body(f)["data"]:
            ks = {m["id"]}
            c = m.get("canonical_slug")
            if c:
                if ":" in m["id"] and ":" not in c:
                    ks.add(c + ":" + m["id"].split(":", 1)[1])  # a variant never claims the bare slug
                else:
                    ks.add(c)
            p = m.get("pricing") or {}
            for k in ks:
                by_key.setdefault(k, []).append({
                    "date": sd, "prompt": p.get("prompt"), "completion": p.get("completion"),
                    "has_hf": "hugging_face_id" in m, "hf": m.get("hugging_face_id") or ""})

    def price(slug, base, variant, month):
        mid = dt.date(int(month[:4]), int(month[5:7]), 15)
        for k in (slug, base):
            c = [x for x in by_key.get(k, []) if x["prompt"] not in (None, "") and x["completion"] not in (None, "")]
            if c:
                best = min(c, key=lambda x: (abs((x["date"] - mid).days), -x["date"].toordinal()))
                return 1e6 * (W_IN * float(best["prompt"]) + (1 - W_IN) * float(best["completion"]))
        return 0.0 if variant == "free" else None

    def open_w(slug, base, prefix):
        if slug == "other" or prefix in ("stealth", "openrouter"):
            return None
        for k in (slug, base):
            c = by_key.get(k)
            if c:
                if any(x["hf"] for x in c):
                    return True
                if any(x["has_hf"] for x in c):
                    return False
        return None

    mm = d.groupby(["month", "model_permaslug", "base", "variant", "prefix", "family", "org", "group"],
                   as_index=False)["tokens"].sum()
    mm["price"] = [price(r.model_permaslug, r.base, r.variant, r.month) if r.model_permaslug != "other" else None
                   for r in mm.itertuples()]
    mm["spend"] = mm["tokens"] * mm["price"] / 1e6
    ow = {s: open_w(s, b, p) for s, b, p in d[["model_permaslug", "base", "prefix"]].drop_duplicates().itertuples(index=False)}
    mm["open_weights"] = mm["model_permaslug"].map(ow)
    return d, mm


def key_numbers(d, mm):
    k = {}
    tot_m = d.groupby("month")["tokens"].sum()
    k["Total tokens, all days"] = int(d["tokens"].sum())
    k["Tokens, 2025-01"] = int(tot_m["2025-01"])
    k["Tokens, 2026-09"] = int(tot_m["2026-09"])
    k["Avg tokens per day, 2026-09"] = tot_m["2026-09"] / d[d.month == "2026-09"]["date"].nunique()
    for mo in MONTHS:
        g = mm[mm.month == mo].groupby("group")["tokens"].sum() / tot_m[mo]
        for grp in ("China", "US", "Europe", "Stealth", "Long tail"):
            k[f"Token share {grp}, {mo}"] = float(g.get(grp, 0.0))
    sep = mm[mm.month == "2026-09"]
    lab = sep.groupby("org")["tokens"].sum().sort_values(ascending=False)
    k["Top organization, 2026-09"] = lab.index[0]
    k["Top organization share, 2026-09"] = lab.iloc[0] / tot_m["2026-09"]
    for mo in ("2025-01", "2026-09"):
        x = mm[(mm.month == mo) & (mm.model_permaslug != "other")]
        fam = x.groupby("family")["tokens"].sum()
        k[f"HHI family, {mo}"] = float(10000 * ((fam / fam.sum()) ** 2).sum())
        labs = x[~x.org.isin(["Stealth (unnamed lab)"])].groupby("org")["tokens"].sum()
        k[f"HHI lab, {mo}"] = float(10000 * ((labs / labs.sum()) ** 2).sum())
        k[f"Top-5 family share, {mo}"] = fam.sort_values(ascending=False).head(5).sum() / tot_m[mo]
    k["Open-weight share, 2026-09"] = sep.loc[sep.open_weights == True, "tokens"].sum() / tot_m["2026-09"]  # noqa: E712
    k["Free-variant share, 2026-09"] = sep.loc[sep.variant == "free", "tokens"].sum() / tot_m["2026-09"]
    for mo in ("2025-01", "2026-09"):
        x = mm[(mm.month == mo) & mm.spend.notna()]
        k[f"Average price paid $/M, {mo}"] = x.spend.sum() / x.tokens.sum() * 1e6
        g = x.groupby("group")["spend"].sum() / x.spend.sum()
        k[f"Spend share China, {mo}"] = float(g.get("China", 0.0))
        k[f"Spend share US, {mo}"] = float(g.get("US", 0.0))
    priced = mm[mm.model_permaslug != "other"]
    k["Named tokens with a price"] = priced.loc[priced.price.notna(), "tokens"].sum() / priced.tokens.sum()

    # Category mix, September 2026: only buckets inside each pull's own window
    cat_rows = []
    for f in glob.glob(str(RAW / "rankings_category_month" / "*.json")):
        b = body(f)
        cat = Path(f).stem.rsplit("_", 2)[0]
        cat_rows += [{"cat": cat, "month": x["date"], "slug": x["model_permaslug"], "tokens": int(x["total_tokens"])}
                     for x in b["data"] if x["date"] >= b["meta"]["start_date"]]
    c = pd.DataFrame(cat_rows)
    c = c[c.month == "2026-09-01"]
    k["Programming share of category tokens, 2026-09"] = c[c.cat == "programming"].tokens.sum() / c.tokens.sum()
    prog = c[c.cat == "programming"].copy()
    labs = pd.read_csv(ROOT / "data" / "reference" / "labs.csv", dtype=str)
    china_prefixes = set(labs[labs.hq_country == "China"].prefix)
    prog["china"] = prog.slug.str.split("/").str[0].isin(china_prefixes)
    k["China share of programming, 2026-09"] = prog[prog.china].tokens.sum() / prog.tokens.sum()

    a = body(str(RAW / "app_rankings_month" / "2026-09.json"))["data"]
    top = max(a, key=lambda x: int(x["total_tokens"]))
    k["Top app, 2026-09"] = top["app_name"]
    k["Top app share of month tokens, 2026-09"] = int(top["total_tokens"]) / tot_m["2026-09"]

    # Launch curves: families first seen on/after 2025-02-01; peak week within weeks 0-25
    day_tot = d.groupby("date")["tokens"].sum()
    fam_day = d[d.model_permaslug != "other"].groupby(["family", "date"])["tokens"].sum()
    first = fam_day.reset_index().groupby("family")["date"].min()
    first = first[first >= "2025-02-01"]
    all_days = sorted(day_tot.index)
    peaks = []
    for fam, f0 in first.items():
        f0d = dt.date.fromisoformat(f0)
        weeks = {}
        for day in all_days:
            gap = (dt.date.fromisoformat(day) - f0d).days
            if 0 <= gap <= 181:
                share = fam_day.get((fam, day), 0) / day_tot[day]
                weeks.setdefault(gap // 7, []).append(share)
        avg = {w: sum(v) / len(v) for w, v in weeks.items()}
        peaks.append(max(avg, key=lambda w: (avg[w], -w)))
    k["Families launched in window"] = len(first)
    k["Median peak week after launch"] = float(pd.Series(peaks).median())
    return k


# ---------- model side: the DuckDB marts ----------

def model_numbers():
    con = duckdb.connect(str(ROOT / "data" / "model.duckdb"), read_only=True)
    q = lambda sql, *p: con.execute(sql, list(p)).fetchone()[0]
    m = {}
    m["Total tokens, all days"] = q("SELECT sum(tokens) FROM fct_model_day")
    m["Tokens, 2025-01"] = q("SELECT sum(tokens) FROM mart_lab_month WHERE month = DATE '2025-01-01'")
    m["Tokens, 2026-09"] = q("SELECT sum(tokens) FROM mart_lab_month WHERE month = DATE '2026-09-01'")
    m["Avg tokens per day, 2026-09"] = q("SELECT sum(avg_tokens_per_day) FROM mart_lab_month WHERE month = DATE '2026-09-01'")
    for mo in MONTHS:
        for grp in ("China", "US", "Europe", "Stealth", "Long tail"):
            m[f"Token share {grp}, {mo}"] = q(
                "SELECT coalesce(sum(token_share), 0) FROM mart_lab_month WHERE month = CAST(? AS DATE) AND country_group = ?",
                mo + "-01", grp)
    m["Top organization, 2026-09"] = q("SELECT org_name FROM mart_lab_month WHERE month = DATE '2026-09-01' ORDER BY tokens DESC LIMIT 1")
    m["Top organization share, 2026-09"] = q("SELECT max(token_share) FROM mart_lab_month WHERE month = DATE '2026-09-01'")
    for mo in ("2025-01", "2026-09"):
        m[f"HHI family, {mo}"] = q("SELECT hhi_family FROM mart_concentration_month WHERE month = CAST(? AS DATE)", mo + "-01")
        m[f"HHI lab, {mo}"] = q("SELECT hhi_lab FROM mart_concentration_month WHERE month = CAST(? AS DATE)", mo + "-01")
        m[f"Top-5 family share, {mo}"] = q("SELECT top5_family_share FROM mart_concentration_month WHERE month = CAST(? AS DATE)", mo + "-01")
    m["Open-weight share, 2026-09"] = q("SELECT sum(open_weight_tokens) / sum(tokens) FROM mart_lab_month WHERE month = DATE '2026-09-01'")
    m["Free-variant share, 2026-09"] = q("SELECT sum(free_variant_tokens) / sum(tokens) FROM mart_lab_month WHERE month = DATE '2026-09-01'")
    for mo in ("2025-01", "2026-09"):
        m[f"Average price paid $/M, {mo}"] = q(
            "SELECT sum(est_spend_usd) / sum(priced_tokens) * 1e6 FROM mart_lab_month WHERE month = CAST(? AS DATE)", mo + "-01")
        m[f"Spend share China, {mo}"] = q(
            "SELECT coalesce(sum(spend_share), 0) FROM mart_lab_month WHERE month = CAST(? AS DATE) AND country_group = 'China'", mo + "-01")
        m[f"Spend share US, {mo}"] = q(
            "SELECT coalesce(sum(spend_share), 0) FROM mart_lab_month WHERE month = CAST(? AS DATE) AND country_group = 'US'", mo + "-01")
    m["Named tokens with a price"] = q("""SELECT sum(tokens) FILTER (WHERE est_spend_usd IS NOT NULL) / sum(tokens)
        FROM mart_model_month WHERE model_permaslug <> 'other'""")
    m["Programming share of category tokens, 2026-09"] = q("""SELECT sum(tokens) FILTER (WHERE category = 'programming') / sum(tokens)
        FROM mart_category_month WHERE month = DATE '2026-09-01'""")
    m["China share of programming, 2026-09"] = q("""SELECT sum(share_in_category) FROM mart_category_month
        WHERE month = DATE '2026-09-01' AND category = 'programming' AND country_group = 'China'""")
    m["Top app, 2026-09"] = q("SELECT app_name FROM mart_app_month WHERE month = DATE '2026-09-01' ORDER BY tokens DESC LIMIT 1")
    m["Top app share of month tokens, 2026-09"] = q("SELECT max(share_of_month_tokens) FROM mart_app_month WHERE month = DATE '2026-09-01'")
    m["Families launched in window"] = q("SELECT count(DISTINCT model_family) FROM mart_launch_weekly")
    m["Median peak week after launch"] = q("""SELECT median(peak) FROM (
        SELECT model_family, arg_max(weeks_since_launch, avg_daily_share * 1e6 - weeks_since_launch * 1e-9) AS peak
        FROM mart_launch_weekly GROUP BY 1)""")
    return m


def fmt(name, v):
    if isinstance(v, str):
        return v
    if "share" in name.lower() or name == "Named tokens with a price":
        return f"{100 * v:.2f}%"
    if "HHI" in name:
        return f"{v:,.0f}"
    if "$/M" in name:
        return f"${v:.4f}"
    if "week" in name.lower():
        return f"{v:g}"
    return f"{v:,.0f}"


def same(a, b):
    if isinstance(a, str) or isinstance(b, str):
        return a == b
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) <= 1e-9 * max(1.0, abs(float(a)))


def main():
    d, mm = load_key()
    k, m = key_numbers(d, mm), model_numbers()
    lines = ["# Answer key", "",
             "Generated by `scripts/answer_key.py`. The key side is pandas reading only the raw JSON pulls and",
             "`data/reference/labs.csv`. The model side is the DuckDB marts the dashboards read. A row passes when",
             "the two agree to 9 significant digits (text values must be identical).", "",
             "| Check | Answer key (pandas) | Model (DuckDB) | Match |", "|---|---|---|---|"]
    bad = 0
    for name, kv in k.items():
        mv = m.get(name)
        ok = same(kv, mv)
        bad += not ok
        lines.append(f"| {name} | {fmt(name, kv)} | {fmt(name, mv) if mv is not None else 'n/a'} | {'PASS' if ok else 'FAIL'} |")
    lines += ["", f"**{len(k) - bad} of {len(k)} checks match.**"]
    (ROOT / "docs" / "ANSWER_KEY.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
