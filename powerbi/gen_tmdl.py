"""measures.dax + the published CSVs -> powerbi/model_full.tmdl for Power BI's TMDL view (web).

    python powerbi/gen_tmdl.py

Adapted from Ajay0704/ecommerce-powerbi (powerbi/gen_tmdl.py). Every table except the seed table (dim_lab,
created through Power Query Online's "Link to file") is defined here with explicit column types and an M
partition reading the CSV from this repo on GitHub. One data source (raw.githubusercontent.com, anonymous,
privacy Public) via RelativePath, so the service needs a single credential and no gateway.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
ROOT = HERE.parent
SOURCE_BASE = "https://raw.githubusercontent.com"
REPO_PATH = "Ajay0704/ai-model-market/main"
SEED_TABLE = "dim_lab"

# table -> CSV path in the repo. Star schema first, then the small chart-ready tables Tableau also reads.
TABLES = {
    "dim_lab": "data/processed/dim_lab.csv",  # replaces the untyped seed table (no date columns, so a full replace is safe)
    "dim_date": "data/processed/dim_date.csv",
    "dim_month": "data/processed/dim_month.csv",
    "dim_model": "data/processed/dim_model.csv",
    "fct_model_day": "data/processed/fct_model_day.csv",
    "mart_model_month": "data/processed/mart_model_month.csv",
    "chart_price_tiers": "tableau/data/price_tiers.csv",
    "chart_price_index": "tableau/data/price_index.csv",
    "chart_quality_price": "tableau/data/quality_price.csv",
    "chart_china_labs": "tableau/data/china_labs.csv",
    "chart_robustness": "tableau/data/robustness.csv",
    "chart_launch_curve": "tableau/data/launch_curve.csv",
    "chart_categories": "tableau/data/categories.csv",
    "chart_top_apps": "tableau/data/top_apps.csv",
    "chart_labs_tokens_spend": "tableau/data/labs_tokens_spend.csv",
}
# (from table, column) -> (to table, column); all many-to-one, single direction
RELATIONSHIPS = [
    ("fct_model_day", "date", "dim_date", "date"),
    ("dim_date", "month", "dim_month", "month"),
    ("fct_model_day", "model_permaslug", "dim_model", "model_permaslug"),
    ("dim_model", "org_name", "dim_lab", "org_name"),
    ("mart_model_month", "month", "dim_month", "month"),
    ("mart_model_month", "model_permaslug", "dim_model", "model_permaslug"),
]
HOME = {"Tokens": "fct_model_day", "Spend": "mart_model_month", "Charts": "mart_model_month", "Robustness": "chart_robustness"}
DATES = {"date", "month", "week_start", "listed_date", "first_seen_date", "last_seen_date", "Month", "Week"}
BOOLS = {"is_missing_day", "is_partial", "is_free_variant", "is_stealth", "open_weights"}
INTS = {"tokens", "days_in_top50", "data_days", "month_sort", "year", "context_length", "Tier Order", "Lab Order",
        "Cut Order", "Rank", "Weeks Since Launch", "Spend Rank", "Group Order"}
SORT_BY = {("dim_month", "month_label"): "month_sort", ("chart_price_tiers", "Tier"): "Tier Order",
           ("chart_robustness", "Way of Counting"): "Cut Order", ("chart_china_labs", "Lab"): "Lab Order",
           ("chart_labs_tokens_spend", "Lab"): "Spend Rank"}
COLUMN_FORMATS = {
    ("chart_price_tiers", "Share"): "0.0%", ("chart_china_labs", "Share"): "0.0%", ("chart_categories", "Share"): "0.0%",
    ("chart_top_apps", "Share of September Tokens"): "0.0%", ("chart_labs_tokens_spend", "Share"): "0.0%",
    ("chart_price_index", "Index (Jan 2025 = 100)"): "0", ("chart_launch_curve", "Share (% of peak)"): "0", ("chart_quality_price", "Share of 90-day Tokens"): "0.00%",
    ("chart_quality_price", "Price per M"): r"\$#,0.00", ("mart_model_month", "token_share"): "0.0%",
    ("mart_model_month", "est_spend_usd"): r"\$#,0", ("mart_model_month", "blended_price_per_m"): r"\$#,0.00",
}


def fmt_measure(name: str) -> str | None:
    n = name.lower()
    if "share" in n:
        return "0.0%"
    if "hhi" in n or "line" in n:
        return "#,0"
    if "per day" in n:
        return "#,0.0"
    if "price" in n:
        return r"\$#,0.00"
    if "spend" in n:
        return r"\$#,0"
    return "#,0"


def parse_measures(text: str) -> list[tuple[str, str, str]]:
    """-> [(folder, name, expression)]; same parser as the Olist project."""
    out, folder, cur, prev_sep = [], None, None, True
    for raw in text.splitlines() + [""]:
        header = re.match(r"^// -+ (.+?) -+\s*$", raw)
        if header:
            folder = header.group(1)
        starts = re.match(r"^([A-Za-z0-9][^=/]*?) =(.*)$", raw)
        is_start = bool(starts) and prev_sep and not re.match(r"^(VAR|RETURN)\b", raw)
        prev_sep = raw.strip() == "" or raw.startswith("//")
        if is_start:
            if cur:
                out.append(cur)
            cur = (folder, starts.group(1).strip(), [starts.group(2).strip()] if starts.group(2).strip() else [])
            continue
        if cur and (raw.strip() == "" or raw.startswith("//")):
            out.append(cur)
            cur = None
            continue
        if cur:
            cur[2].append(raw.rstrip())
    return [(f, n, "\n".join(e).strip()) for f, n, e in out]


def qn(name: str) -> str:
    """TMDL object name, quoted when it has spaces or punctuation."""
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else "'" + name.replace("'", "''") + "'"


def measure_tmdl(folder: str, name: str, expr: str) -> list[str]:
    lines = expr.splitlines()
    out = [f"\t\tmeasure {qn(name)} = {lines[0]}"] if len(lines) == 1 else \
        [f"\t\tmeasure {qn(name)} = ```"] + [f"\t\t\t\t{l}" for l in lines if l.strip()] + ["\t\t\t\t```"]
    f = fmt_measure(name)
    return out + ([f"\t\t\tformatString: {f}"] if f else []) + [f"\t\t\tdisplayFolder: {folder}", ""]


def csv_types(path: str) -> list[tuple[str, str, str]]:
    df = pd.read_csv(ROOT / path, nrows=20000)
    out = []
    for c, dt in df.dtypes.items():
        if c in DATES:
            out.append((c, "dateTime", "type date"))
        elif c in BOOLS:
            out.append((c, "boolean", "type logical"))
        elif c in INTS:
            out.append((c, "int64", "Int64.Type"))
        elif str(dt).startswith(("float", "int")):
            out.append((c, "double", "type number"))
        else:
            out.append((c, "string", "type text"))
    return out


def table_tmdl(table: str, path: str, measures: list) -> list[str]:
    cols = csv_types(path)
    lines = [f"\ttable {table}"] + (["\t\tdataCategory: Time"] if table == "dim_date" else []) + [""]
    for m in measures:
        lines += measure_tmdl(*m)
    for c, dt, _ in cols:
        lines += [f"\t\tcolumn {qn(c)}", f"\t\t\tdataType: {dt}"]
        if (table, c) in {("dim_date", "date")}:
            lines.append("\t\t\tisKey")
        f = COLUMN_FORMATS.get((table, c)) or ("yyyy-mm-dd" if dt == "dateTime" else None)
        if f:
            lines.append(f"\t\t\tformatString: {f}")
        if c in {"month_sort", "Tier Order", "Cut Order", "Lab Order", "Spend Rank"}:
            lines.append("\t\t\tisHidden")
        lines.append(f"\t\t\tsummarizeBy: {'sum' if c in {'tokens', 'est_spend_usd', 'est_spend_usd_3to1'} else 'none'}")
        lines.append(f"\t\t\tsourceColumn: {c}")
        if (table, c) in SORT_BY:
            lines.append(f"\t\t\tsortByColumn: {qn(SORT_BY[(table, c)])}")
        lines.append("")
    pairs = ", ".join(f'{{"{c}", {pq}}}' for c, _, pq in cols)
    lines += [
        f"\t\tpartition {table} = m",
        "\t\t\tmode: import",
        "\t\t\tsource =",
        "\t\t\t\t\tlet",
        f'\t\t\t\t\t\tSource = Csv.Document(Web.Contents("{SOURCE_BASE}", [RelativePath = "{REPO_PATH}/{path}"]), '
        '[Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
        "\t\t\t\t\t\tHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),",
        f'\t\t\t\t\t\tTyped = Table.TransformColumnTypes(Headers, {{{pairs}}}, "en-US")',
        "\t\t\t\t\tin",
        "\t\t\t\t\t\tTyped",
        "",
    ]
    return lines


def main() -> None:
    measures = parse_measures((HERE / "measures.dax").read_text())
    by_table: dict[str, list] = {}
    for m in measures:
        by_table.setdefault(HOME[m[0]], []).append(m)
    lines = ["createOrReplace", ""]
    for t, path in TABLES.items():
        lines += table_tmdl(t, path, by_table.get(t, []))
    for ft, fc, tt, tc in RELATIONSHIPS:
        lines += [f"\trelationship {ft}_{fc}__{tt}", f"\t\tfromColumn: {ft}.{qn(fc)}", f"\t\ttoColumn: {tt}.{qn(tc)}", ""]
    (HERE / "model_full.tmdl").write_text("\n".join(lines) + "\n")
    print(f"{len(TABLES)} tables (+ seed {SEED_TABLE}), {len(measures)} measures, {len(RELATIONSHIPS)} relationships -> powerbi/model_full.tmdl")


if __name__ == "__main__":
    main()
