"""Write the flat CSVs the Tableau workbook reads (tableau/data/*.csv), from mockup/data.json.

The mockup's export is the single source of numbers, so Tableau and the approved mockup can't disagree.
Usage: python analysis/export_mockup_data.py && python analysis/export_tableau_data.py
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = json.loads((ROOT / "mockup" / "data.json").read_text())
OUT = ROOT / "tableau" / "data"
OUT.mkdir(parents=True, exist_ok=True)
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
mlabel = lambda m: f"{MON[int(m[5:7]) - 1]} {m[2:4]}"
pct = lambda v: f"{100 * v:.1f}%"


def write(name, header, rows):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"{name}: {len(rows)} rows")


# 1 Leadership
weeks = {}
for r in D["weekly_share"]:
    g = r["g"] if r["g"] in ("China", "US") else "Everyone else"
    weeks.setdefault(r["week"], {}).setdefault(g, 0.0)
    weeks[r["week"]][g] += r["share"]
write("weekly_share.csv", ["Week", "Group", "Share"],
      [[wk, g, round(v, 6)] for wk in sorted(weeks) for g, v in weeks[wk].items()])
vol = D["monthly_volume"]
write("daily_volume.csv", ["Month", "Month Label", "Tokens per Day (T)", "Status", "Bar Label"],
      [[r["month"] + "-01", mlabel(r["month"]), round(r["per_day_t"], 4), "Partial month" if r["partial"] else "Full month",
        (f"{r['per_day_t'] * 1000:.0f}B" if r["per_day_t"] < 1 else f"{r['per_day_t']:.1f}T") if r["month"] in ("2025-01", "2026-09") else ""]
       for r in vol])
write("hhi.csv", ["Month", "Lab HHI", "Line 1800", "Status"],
      [[r["month"] + "-01", round(r["hhi_lab"], 1), 1800, "Partial month" if r["partial"] else "Full month"] for r in D["hhi"]])

# 2 Pricing
GNAME = {"China": "China", "US": "US", "Unattributed": "Stealth + long tail", "Other named": "Other countries"}
write("groups_tokens_spend.csv", ["Group", "Group Order", "Measure", "Share"],
      [[GNAME[r["g"]], ["China", "US", "Unattributed", "Other named"].index(r["g"]) + 1, m, round(r[k], 6)]
       for r in D["group_tokens_vs_spend"] for m, k in (("Share of tokens", "tok"), ("Share of estimated spend", "spend"))])
write("labs_tokens_spend.csv", ["Lab", "Spend Rank", "Measure", "Share"],
      [[r["lab"], i + 1, m, round(r[k], 6)] for i, r in enumerate(D["lab_tokens_vs_spend"])
       for m, k in (("Share of tokens", "tok"), ("Share of estimated spend", "spend"))])
TIERS = ["Free", "Under $0.25", "$0.25-1", "$1-5", "$5+"]
tier = {r["tier"]: r for r in D["tiers"]}
write("price_tiers.csv", ["Tier", "Tier Order", "Measure", "Share"],
      [[t, i + 1, m, round(tier[t][k], 6)] for i, t in enumerate(TIERS) for m, k in (("Share of tokens", "tok"), ("Share of estimated spend", "spend"))])
write("price_index.csv", ["Month", "Series", "Index (Jan 2025 = 100)"],
      [[r["month"] + "-01", s, round(100 * r[k], 2)] for r in D["price_index"]
       for s, k in (("Average price paid", "avg_idx"), ("Same-model list price", "same_model_idx"))])

# 3 AI platform
top_used = {r["name"] for r in sorted(D["scatter"], key=lambda r: -r["share"])[:5]}
frontier = {r["name"] for r in D["frontier"]}
short = lambda n: n.split(" (")[0]
write("quality_price.csv", ["Model", "Lab", "Group", "Intelligence Index", "Price per M", "Share of 90-day Tokens", "Point Label", "Highlight"],
      [[r["name"], r["lab"], r["g"], r["iq"], round(r["price"], 4), round(r["share"], 6),
        short(r["name"]) if (r["name"] in top_used or r["name"] in frontier) else "",
        "Top 5 by usage" if r["name"] in top_used else "Price-quality frontier" if r["name"] in frontier else "Other"]
       for r in D["scatter"]])

# 4 Competitive intel
last = {r["lab"]: r["share"] for r in D["china_labs"] if r["month"] == "2026-09"}
order = sorted(last, key=lambda k: -last[k])
write("china_labs.csv", ["Lab", "Lab Order", "Lab Title", "Month", "Share"],
      [[r["lab"], order.index(r["lab"]) + 1, f"{r['lab']}  ·  {pct(last[r['lab']])} in Sep", r["month"] + "-01", round(r["share"], 6)]
       for r in D["china_labs"]])
CUTS = ["as measured", "all stealth + long tail credited to the US", "paid tokens only", "without DeepSeek"]
rows = []
for i, cut in enumerate(CUTS):
    for r in [x for x in D["robustness"] if x["cut"] == cut]:
        who = "China ahead" if r["china"] > r["us"] else "US ahead"
        rows.append([cut[0].upper() + cut[1:], i + 1, r["month"] + "-01", f"{who}   {pct(r['china'])} vs {pct(r['us'])}", who,
                     mlabel(r["month"]).replace(" ", " 20"), int(r["month"].replace("-", ""))])
rq = D["requests_week"]
rows.append(["By requests, not tokens (week of Oct 12)", 5, "2026-09-01", f"Tie   {pct(rq['china'])} vs {pct(rq['us'])}", "Tie", "Sep 2026", 202609])
write("robustness.csv", ["Way of Counting", "Cut Order", "Month", "Result", "Leader", "Month Label", "Month Sort"], rows)

# 5 Product & GTM
write("launch_curve.csv", ["Weeks Since Launch", "Series", "Share (% of peak)"],
      [[r["w"], s, round(100 * r[k], 2)] for r in D["launch"] for s, k in (("The lab", "lab_vs_base"), ("The model", "model_vs_peak"))])
write("categories.csv", ["Month", "Category", "Share"],
      [[r["month"] + "-01", r["category"].title(), round(r["share"], 6)] for r in D["categories"] if r["category"] in ("programming", "roleplay")])
write("top_apps.csv", ["App", "Rank", "Share of September Tokens"],
      [[a["app"], i + 1, round(a["share"], 6)] for i, a in enumerate(D["apps"])])
