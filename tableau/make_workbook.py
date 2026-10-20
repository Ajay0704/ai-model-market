"""Build tableau/AI_Model_Market.twbx: five stakeholder dashboards and a story, matching the approved mockup.

Numbers come from mockup/data.json (via analysis/export_tableau_data.py), the same export the approved
mockup draws, so titles and KPI tiles can't drift from the verified answer key.
Usage: python analysis/export_tableau_data.py && python tableau/make_workbook.py [--open-on N]
"""

import argparse
import csv
import json
import zipfile
from pathlib import Path

from tableau_xml import BOOK, INK, INK2, MUTED, SEMI, Datasource, Field, Sheet, dashboard, run, story, workbook

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "data"
NAME = "AI_Model_Market"
D = json.loads((ROOT / "mockup" / "data.json").read_text())

CHINA, US, GRAY, ACCENT, ACCENT_LIGHT = "#2a78d6", "#eb6834", "#898781", "#6250d6", "#b9b0f0"
SOURCE = "Source: OpenRouter (openrouter.ai/rankings), as of 2026-10-19 · CC BY 4.0"
DATES = {"Week", "Month"}
INTS = {"Group Order", "Spend Rank", "Tier Order", "Lab Order", "Cut Order", "Rank", "Line 1800", "Weeks Since Launch"}


def cols(fn):
    header = next(csv.reader(open(DATA / fn, encoding="utf-8")))
    out = []
    for h in header:
        if h in DATES:
            out.append((h, "date"))
        elif h in INTS:
            out.append((h, "integer"))
        else:
            sample = next(csv.DictReader(open(DATA / fn, encoding="utf-8")))[h]
            try:
                float(sample)
                out.append((h, "real"))
            except ValueError:
                out.append((h, "string"))
    return out


def ds(key, caption, fn, **kw):
    return Datasource(key.ljust(28, "0")[:28], caption, "Data/data", fn, cols(fn), **kw)


pct, pct1, num = "p0%", "p0.0%", "n0"
meas = {"Share of tokens": GRAY, "Share of estimated spend": ACCENT}
S = {
    "weekly": ds("0weekly", "Weekly share", "weekly_share.csv", palettes={"Group": {"China": CHINA, "US": US, "Everyone else": GRAY}}, formats={"Share": pct}),
    "volume": ds("0volume", "Daily volume", "daily_volume.csv", palettes={"Status": {"Full month": ACCENT, "Partial month": ACCENT_LIGHT}}, formats={"Tokens per Day (T)": num}),
    "hhi": ds("0hhi", "Concentration", "hhi.csv", formats={"Lab HHI": num}),
    "groups": ds("0groups", "Groups: tokens vs spend", "groups_tokens_spend.csv", palettes={"Measure": meas}, formats={"Share": pct}),
    "labs": ds("0labs", "Labs: tokens vs spend", "labs_tokens_spend.csv", palettes={"Measure": meas}, formats={"Share": pct}),
    "tiers": ds("0tiers", "Price tiers", "price_tiers.csv", palettes={"Measure": meas}, formats={"Share": pct}),
    "pidx": ds("0priceidx", "Price index", "price_index.csv", palettes={"Series": {"Average price paid": ACCENT, "Same-model list price": GRAY}},
               formats={"Index (Jan 2025 = 100)": num}),
    "qp": ds("0quality", "Quality vs price", "quality_price.csv", palettes={"Group": {"China": CHINA, "US": US, "Other": GRAY}},
             formats={"Share of 90-day Tokens": "p0.00%", "Price per M": "*$#,##0.00", "Intelligence Index": "n0.0"}),
    "cn": ds("0chinalabs", "Chinese labs", "china_labs.csv", formats={"Share": pct}),
    "rob": ds("0robust", "Robustness", "robustness.csv"),
    "launch": ds("0launch", "Launch curve", "launch_curve.csv", palettes={"Series": {"The lab": ACCENT, "The model": GRAY}},
                 formats={"Share (% of peak)": num}, dims={"Weeks Since Launch"}),
    "cats": ds("0categories", "Categories", "categories.csv", palettes={"Category": {"Programming": ACCENT, "Roleplay": GRAY}}, formats={"Share": pct}),
    "apps": ds("0apps", "Top apps", "top_apps.csv", formats={"Share of September Tokens": pct1}),
}

# ---------- numbers for titles and KPI tiles (same logic as the mockup) ----------
K = D["kpi"]
growth = K["tokens_sep"] / K["tokens_jan25"]
vol = {r["month"]: r for r in D["monthly_volume"]}
hhi_full = [r for r in D["hhi"] if not r["partial"]]
hhi_min = min(hhi_full, key=lambda r: r["hhi_lab"])
last_above = max(i for i, r in enumerate(hhi_full) if r["hhi_lab"] >= 1800)
below_since = hhi_full[last_above + 1]
first_below = next(r for r in hhi_full if r["hhi_lab"] < 1800)
G = {r["g"]: r for r in D["group_tokens_vs_spend"]}
P0, P1 = D["price_index"][0], D["price_index"][-1]
tier = {r["tier"]: r for r in D["tiers"]}
cheap_tok, cheap_spend = tier["Free"]["tok"] + tier["Under $0.25"]["tok"], tier["Free"]["spend"] + tier["Under $0.25"]["spend"]
H6 = D["h6"]
rob = lambda cut, m: next(r for r in D["robustness"] if r["cut"] == cut and r["month"] == m)
WORST = "all stealth + long tail credited to the US"
cn_2pct = sum(1 for r in D["china_labs"] if r["month"] == "2026-09" and r["share"] >= 0.02)
LS = {r["cut"]: r for r in D["launch_split"]}
cat = lambda m, c: next(r["share"] for r in D["categories"] if r["month"] == m and r["category"] == c)
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
mname = lambda m: f"{MON[int(m[5:7]) - 1]} {m[:4]}"
P = lambda v, d=1: f"{100 * v:.{d}f}%"
T = lambda v: f"{v:.0f}T" if v >= 100 else f"{v:.1f}T" if v >= 1 else f"{v * 1000:.0f}B"
PTS = lambda v: ("+" if v >= 0 else "−") + f"{abs(100 * v):.1f} pts"
USD = lambda v: f"${v:.2f}"
lab0 = D["lab_tokens_vs_spend"][0]

f = lambda d, c, k=None: Field(d, c, k)
n = lambda c: Field("none", c)


def sheets():
    s = S
    return [
        Sheet("Weekly share", s["weekly"], "China first passed the US the week of Mar 23, 2026, and has led every week since Apr 27",
              f"Share of weekly tokens · Jan 2025 to Oct 18, 2026 · {SOURCE}",
              rows=[f("sum", "Share")], cols=[f("none", "Week", "qk")], mark="Line", color=n("Group"),
              labels=True, label_mode="line-ends", text=[n("Group"), f("sum", "Share")], label_formats={f("sum", "Share"): pct1},
              axis_ranges=[(f("sum", "Share"), "rows", 0, 1)], hide_titles=[(f("sum", "Share"), "rows"), (f("none", "Week", "qk"), "cols")]),
        Sheet("Daily volume", s["volume"], f"Daily volume grew from {T(vol['2025-01']['per_day_t'])} to {T(vol['2026-09']['per_day_t'])} tokens a day",
              f"Average tokens per day (trillions), by month · Oct 2026 runs to the 18th · {SOURCE}",
              rows=[f("sum", "Tokens per Day (T)")], cols=[f("tmn", "Month", "qk")], mark="Bar", color=n("Status"),
              labels=True, text=[f("attr", "Bar Label", "nk")],
              hide_titles=[(f("sum", "Tokens per Day (T)"), "rows"), (f("tmn", "Month", "qk"), "cols")]),
        Sheet("Concentration", s["hhi"], f"Lab concentration fell from {K['hhi_jan25']:,.0f} to a low of {hhi_min['hhi_lab']:,.0f} ({mname(hhi_min['month'])}), then rose to {K['hhi_sep']:,.0f}",
              f"Herfindahl-Hirschman Index of lab shares, full months · line at 1,800 · {SOURCE}",
              rows=[f("sum", "Lab HHI")], cols=[f("tmn", "Month", "qk")], mark="Line", mark_color=ACCENT,
              labels=True, label_mode="most-recent", filters={"Status": ["Full month"]},
              refline=dict(axis=f("sum", "Lab HHI"), value=f("avg", "Line 1800"), label='1,800: "highly concentrated" (DOJ/FTC 2023 guidelines)'),
              axis_ranges=[(f("sum", "Lab HHI"), "rows", 0, 3500)], hide_titles=[(f("sum", "Lab HHI"), "rows"), (f("tmn", "Month", "qk"), "cols")]),
        Sheet("Groups: tokens vs spend", s["groups"], f"China: {P(G['China']['tok'])} of tokens, {P(G['China']['spend'])} of spend",
              f"Share of tokens (gray) vs share of estimated spend (violet) · September 2026 · {SOURCE}",
              rows=[n("Group")], cols=[f("sum", "Share")], mark="Circle", color=n("Measure"), labels=True, text=[f("sum", "Share")],
              label_formats={f("sum", "Share"): pct1}, manual_sort=("Group", ["China", "US", "Stealth + long tail", "Other countries"]),
              axis_ranges=[(f("sum", "Share"), "cols", 0, 0.7)], hide_titles=[(f("sum", "Share"), "cols")]),
        Sheet("Labs: tokens vs spend", s["labs"], f"{lab0['lab']}: {P(lab0['tok'])} of tokens, {P(lab0['spend'])} of spend",
              f"Top 10 labs by estimated spend · gray = tokens, violet = spend · September 2026 · {SOURCE}",
              rows=[n("Lab")], cols=[f("sum", "Share")], mark="Circle", color=n("Measure"), labels=True, text=[f("sum", "Share")],
              label_formats={f("sum", "Share"): pct1}, manual_sort=("Lab", [r["lab"] for r in D["lab_tokens_vs_spend"]]),
              axis_ranges=[(f("sum", "Share"), "cols", 0, 0.3)], hide_titles=[(f("sum", "Share"), "cols")]),
        Sheet("Price tiers", s["tiers"], f"Models under $0.25 carry {P(cheap_tok)} of tokens but {P(cheap_spend)} of spend",
              f"Blended list price per million tokens · September 2026, priced tokens · {SOURCE}",
              rows=[n("Tier"), n("Measure")], cols=[f("sum", "Share")], mark="Bar", color=n("Measure"), labels=True, text=[f("sum", "Share")],
              label_formats={f("sum", "Share"): pct1},
              manual_sort=[("Tier", ["Free", "Under $0.25", "$0.25-1", "$1-5", "$5+"]), ("Measure", ["Share of tokens", "Share of estimated spend"])],
              hide_headers=[n("Measure")], axis_ranges=[(f("sum", "Share"), "cols", 0, 0.5)], hide_titles=[(f("sum", "Share"), "cols")]),
        Sheet("Price index", s["pidx"], f"The average token got {round((1 - P1['avg_idx']) * 100)}% cheaper; the same models got {round((1 - P1['same_model_idx']) * 100)}% cheaper",
              f"Index, January 2025 = 100 · average price paid vs a chained same-model list-price index · {SOURCE}",
              rows=[f("sum", "Index (Jan 2025 = 100)")], cols=[f("tmn", "Month", "qk")], mark="Line", color=n("Series"),
              labels=True, label_mode="line-ends", text=[n("Series"), f("sum", "Index (Jan 2025 = 100)")],
              axis_ranges=[(f("sum", "Index (Jan 2025 = 100)"), "rows", 0, 120)],
              hide_titles=[(f("sum", "Index (Jan 2025 = 100)"), "rows"), (f("tmn", "Month", "qk"), "cols")]),
        Sheet("Quality vs price", s["qp"], "Usage piles up at low prices and middling scores; the top scorers are niche",
              f"Last 90 days · x: blended price per million tokens (log) · y: Intelligence Index · size: share of tokens · labeled: top 5 by usage and the price-quality frontier · Benchmarks: Artificial Analysis via OpenRouter · {SOURCE}",
              rows=[f("sum", "Intelligence Index")], cols=[f("sum", "Price per M")], mark="Circle", color=n("Group"),
              size=f("sum", "Share of 90-day Tokens"), detail=[n("Model")], labels=True, text=[f("attr", "Point Label", "nk")],
              log_axis=(f("sum", "Price per M"), "cols"), axis_ranges=[(f("sum", "Intelligence Index"), "rows", 10, 60)]),
        Sheet("Chinese labs", s["cn"], "Six Chinese labs on one scale: DeepSeek leads, but others top 5%",
              f"Monthly share of all tokens · Jan 2025 to Sep 2026 · shared y-axis · {SOURCE}",
              rows=[n("Lab Title"), f("sum", "Share")], cols=[f("tmn", "Month", "qk")], mark="Line", mark_color=CHINA,
              labels=True, label_mode="most-recent", label_formats={f("sum", "Share"): pct1},
              manual_sort=("Lab Title", [r for r in dict.fromkeys(x["Lab Title"] for x in sorted(csv.DictReader(open(DATA / "china_labs.csv")), key=lambda x: int(x["Lab Order"])))]),
              hide_titles=[(f("sum", "Share"), "rows"), (f("tmn", "Month", "qk"), "cols")]),
        Sheet("Robustness", s["rob"], "China leads in June and September under every cut, but in March under none",
              f"China vs US share of tokens under four ways of counting · the requests row is from the public rankings page, one week · {SOURCE}",
              rows=[n("Way of Counting")], cols=[f("tmn", "Month", "ok")], mark="Text", text=[f("attr", "Result", "nk")], cell_text=True,
              manual_sort=("Way of Counting", ["As measured", "All stealth + long tail credited to the US", "Paid tokens only", "Without DeepSeek",
                                               "By requests, not tokens (week of Oct 12)"])),
        Sheet("Launch curve", s["launch"], f"By week 12 a model keeps {P(LS['All']['model_w12'], 0)} of its peak; its lab keeps {P(LS['All']['lab_w12'], 0)}",
              f"Median of {LS['All']['n']} launches · indexed to the model's peak week = 100 · {SOURCE}",
              rows=[f("sum", "Share (% of peak)")], cols=[f("none", "Weeks Since Launch", "qk")], mark="Line", color=n("Series"),
              labels=True, label_mode="line-ends", text=[n("Series"), f("sum", "Share (% of peak)")],
              axis_ranges=[(f("sum", "Share (% of peak)"), "rows", 0, 100), (f("none", "Weeks Since Launch", "qk"), "cols", 0, 12)],
              hide_titles=[(f("sum", "Share (% of peak)"), "rows")]),
        Sheet("Categories", s["cats"], f"Programming went from {P(cat('2025-05', 'programming'))} to {P(cat('2026-09', 'programming'))} of categorized tokens",
              f"Monthly share of the 12 categories OpenRouter samples · May 2025 to Sep 2026 · {SOURCE}",
              rows=[f("sum", "Share")], cols=[f("tmn", "Month", "qk")], mark="Line", color=n("Category"),
              labels=True, label_mode="line-ends", text=[n("Category"), f("sum", "Share")], label_formats={f("sum", "Share"): pct1},
              axis_ranges=[(f("sum", "Share"), "rows", 0, 1)], hide_titles=[(f("sum", "Share"), "rows"), (f("tmn", "Month", "qk"), "cols")]),
        Sheet("Top apps", s["apps"], f"Agents top the app chart: {D['apps'][0]['app']} alone drew {P(D['apps'][0]['share'])} of September tokens",
              f"Top 10 apps by tokens, share of all September 2026 tokens · {SOURCE}",
              rows=[n("App")], cols=[f("sum", "Share of September Tokens")], mark="Bar", mark_color=ACCENT, labels=True,
              text=[f("sum", "Share of September Tokens")], sort_by=(n("App"), f("sum", "Share of September Tokens"), "DESC"),
              hide_titles=[(f("sum", "Share of September Tokens"), "cols")]),
    ]


# ---------- dashboards ----------
def header(eyebrow, title, lede):
    return [run(eyebrow + "\n", 9, BOOK, MUTED), run(title + "\n", 19, SEMI, INK, bold=True), run(lede, 10, BOOK, INK2)]


def kpi(label, value, delta):
    return [run(label + "\n", 9, BOOK, INK2), run(value + "\n", 20, SEMI, INK, bold=True), run(delta, 8, BOOK, MUTED)]


def note(bold, text):
    return [run(bold + " ", 9, SEMI, INK, bold=True), run(text, 9, BOOK, INK2)]


def kpis(items):
    return [("card", kpi(*it), 0.25) for it in items]


PAGES = [
    ("1 · Leadership", "Chinese labs have processed more OpenRouter tokens than US labs every week since April 27", [
        (0.13, [("text", header("Leadership · Who is winning, and is the market concentrating?",
                                "Chinese labs have processed more OpenRouter tokens than US labs every week since April 27",
                                f"Volume grew {growth:.0f}-fold in 21 months, and most of it now goes to Chinese labs: {P(K['china_sep'])} of September tokens, up from {P(K['china_jan25'])} in January 2025. "
                                f"Lab concentration has been below the 1,800 \"highly concentrated\" line every month since {mname(below_since['month'])} (it first dipped under in {mname(first_below['month'])}), but it has risen since its {mname(hhi_min['month'])} low."), 1)]),
        (0.11, kpis([("Tokens in September 2026", T(K["tokens_sep"]), f"{growth:.0f}× January 2025 ({T(K['tokens_jan25'])})"),
                     ("China's share of tokens", P(K["china_sep"]), f"{PTS(K['china_sep'] - K['china_jan25'])} vs Jan 2025 ({P(K['china_jan25'])})"),
                     ("US share of tokens", P(K["us_sep"]), f"{PTS(K['us_sep'] - K['us_jan25'])} vs Jan 2025 ({P(K['us_jan25'])})"),
                     ("Lab concentration (HHI)", f"{K['hhi_sep']:,.0f}", f"From {K['hhi_jan25']:,.0f} in Jan 2025 · line is 1,800")])),
        (0.40, [("sheet", "Weekly share", 1)]),
        (0.29, [("sheet", "Daily volume", 0.5), ("sheet", "Concentration", 0.5)]),
        (0.07, [("text", note("Reading it right:", "OpenRouter traffic only, not the whole market. Apps that call OpenAI, Anthropic or Google directly are invisible here. "
                                                 "\"Everyone else\" combines labs outside China and the US with stealth models and the long tail outside each day's top 50."), 1)]),
    ]),
    ("2 · Pricing & finance", "China wins the tokens; US labs still win the money", [
        (0.13, [("text", header("Pricing & finance · Does cheaper win? Where is the money?", "China wins the tokens; US labs still win the money",
                                f"In September, Chinese labs carried {P(G['China']['tok'])} of tokens but an estimated {P(G['China']['spend'])} of spend; US labs carried {P(G['US']['tok'])} of tokens and {P(G['US']['spend'])} of spend. "
                                f"The average token got {round((1 - P1['avg_idx']) * 100)}% cheaper since January 2025, mostly because usage moved to cheaper models: the same models' list prices fell only {round((1 - P1['same_model_idx']) * 100)}%."), 1)]),
        (0.11, kpis([("China's share of spend", P(G["China"]["spend"]), f"vs {P(G['China']['tok'])} of tokens · Sep 2026"),
                     ("US share of spend", P(G["US"]["spend"]), f"vs {P(G['US']['tok'])} of tokens · Sep 2026"),
                     ("Average price paid", USD(P1["avg_price"]) + "/M", f"−{round((1 - P1['avg_idx']) * 100)}% vs Jan 2025 ({USD(P0['avg_price'])}/M)"),
                     ("Same-model list price", f"−{round((1 - P1['same_model_idx']) * 100)}%", "Jan 2025 to Sep 2026, chained index")])),
        (0.34, [("sheet", "Groups: tokens vs spend", 0.5), ("sheet", "Labs: tokens vs spend", 0.5)]),
        (0.34, [("sheet", "Price tiers", 0.5), ("sheet", "Price index", 0.5)]),
        (0.08, [("text", note("Estimated spend", "= tokens × list price, blending input and output 15:1 (OpenRouter's own study reports about 6K prompt vs 400 completion tokens per request). "
                                                 f"It's before caching discounts, so it's an upper bound: use it for shares, not dollar totals. Under a 3:1 blend, China's September spend share is {P(G['China']['spend31'])} and the US's is {P(G['US']['spend31'])}."), 1)]),
    ]),
    ("3 · AI platform", "The most-used models are cheap mid-scorers, not the benchmark leaders", [
        (0.13, [("text", header("AI platform team · Which models give the best quality for the price?", "The most-used models are cheap mid-scorers, not the benchmark leaders",
                                f"The five highest-scoring models (Intelligence Index {H6['scorers_min']}-{H6['scorers_max']}) took {P(H6['top5_scorers'])} of tokens in the last 90 days. "
                                f"The five most-used, scoring {H6['used_min']}-{H6['used_max']}, took {P(H6['top5_used'])}. Only {H6['frontier_n']} of {H6['scored_n']} scored models sit on the price-quality frontier."), 1)]),
        (0.11, kpis([("Top 5 scorers, share of tokens", P(H6["top5_scorers"]), f"Intelligence Index {H6['scorers_min']}-{H6['scorers_max']}"),
                     ("Top 5 most-used, share of tokens", P(H6["top5_used"]), f"Intelligence Index {H6['used_min']}-{H6['used_max']}"),
                     ("Score vs usage, rank correlation", f"{H6['spearman']:.2f}", f"{H6['used_n']} benchmarked models with usage · weak"),
                     ("On the price-quality frontier", f"{H6['frontier_n']} of {H6['scored_n']}", f"{P(H6['frontier_share'])} of benchmarked usage")])),
        (0.68, [("sheet", "Quality vs price", 1)]),
        (0.08, [("text", note("Routing, not taste:", "benchmarks score one setting per model (for example \"Max\" reasoning), while usage counts every setting. "
                                                    "Bulk jobs such as classification, the largest task by requests this week, can rationally use cheap models. One free model is left off the log scale."), 1)]),
    ]),
    ("4 · Competitive intel", "China's lead is broad: it holds without DeepSeek and under the worst-case count", [
        (0.13, [("text", header("Competitive intelligence · Where do the threats come from?", "China's lead is broad: it holds without DeepSeek and under the worst-case count",
                                f"{cn_2pct} Chinese labs each carried 2% or more of September tokens. Credit every unattributed token to the US and China still leads, "
                                f"{P(rob(WORST, '2026-09')['china'])} to {P(rob(WORST, '2026-09')['us'])}. By requests rather than tokens it's a tie, so Chinese models win the long, token-heavy jobs."), 1)]),
        (0.11, kpis([("Chinese labs with 2%+ of tokens", str(cn_2pct), "September 2026"),
                     ("China without DeepSeek", P(rob("without DeepSeek", "2026-09")["china"]), f"vs US {P(rob('without DeepSeek', '2026-09')['us'])} · Sep 2026"),
                     ("US share, worst case for China", P(rob(WORST, "2026-09")["us"]), f"China still {P(rob(WORST, '2026-09')['china'])} · Sep 2026"),
                     ("Share of requests, week of Oct 12", "Tie", f"US {P(D['requests_week']['us'])} · China {P(D['requests_week']['china'])} (public page)")])),
        (0.44, [("sheet", "Chinese labs", 1)]),
        (0.25, [("sheet", "Robustness", 1)]),
        (0.07, [("text", note("Country", "means the developer's stated headquarters, from each lab's own legal or about page (data/reference/labs.csv): "
                                         "not where a model is hosted, and not where a base model it was tuned from came from."), 1)]),
    ]),
    ("5 · Product & GTM", "Models churn within weeks; labs keep most of their users", [
        (0.13, [("text", header("Product & GTM · Do launches stick? What drives demand?", "Models churn within weeks; labs keep most of their users",
                                f"A typical notable launch keeps {P(LS['All']['model_w12'], 0)} of its peak share by week 12, but its lab keeps {P(LS['All']['lab_w12'], 0)}, because users move to the lab's next model. "
                                f"US labs hold on better ({P(LS['US']['lab_w12'], 0)}) than Chinese labs ({P(LS['China']['lab_w12'], 0)}). Coding is now {P(cat('2026-09', 'programming'))} of categorized traffic."), 1)]),
        (0.11, kpis([("A model's share at week 12", P(LS["All"]["model_w12"], 0), f"of its peak · median of {LS['All']['n']} launches"),
                     ("Its lab's share at week 12", P(LS["All"]["lab_w12"], 0), "of the lab's level at the model's peak"),
                     ("US labs keep (week 12)", P(LS["US"]["lab_w12"], 0), f"Chinese labs keep {P(LS['China']['lab_w12'], 0)}"),
                     ("Programming share of categorized tokens", P(cat("2026-09", "programming")), f"From {P(cat('2025-05', 'programming'))} in May 2025")])),
        (0.38, [("sheet", "Launch curve", 0.58), ("sheet", "Categories", 0.42)]),
        (0.30, [("sheet", "Top apps", 1)]),
        (0.08, [("text", note("Launches", "are model families that first entered the daily top 50 on or after Feb 1, 2025, peaked at 1% or more of daily tokens, and have 13+ weeks of data. "
                                          "Stealth models are excluded, because they \"end\" when renamed at launch. A lab that drops out of the top 50 counts as zero."), 1)]),
    ]),
]
STORY = "AI Model Market"


def boards():
    W, H = 1400, 950
    out = []
    for name, _, rows in PAGES:
        members = [c for _, items in rows for k, c, _ in items if k == "sheet"]
        out.append((name, members, dashboard(name, W, H, rows)))
    points = [(name, caption) for name, caption, _ in PAGES]
    out.append((STORY, [], story(STORY, 1400, 1150, points)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--open-on", type=int, default=6, help="tab shown first: 1-5 the dashboards, 6 the story")
    a = ap.parse_args()
    b = boards()
    first = a.open_on - 1
    b = b[first:] + b[:first]
    xml = workbook(list(S.values()), sheets(), b)
    target = HERE / (NAME + ".twbx" if a.open_on == 6 else f"{NAME}_check{a.open_on}.twbx")
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(NAME + ".twb", xml)
        for fcsv in sorted(DATA.glob("*.csv")):
            z.write(fcsv, f"Data/data/{fcsv.name}")
    print(f"Wrote {target.relative_to(ROOT)} ({len(xml):,} bytes of XML)")


if __name__ == "__main__":
    main()
