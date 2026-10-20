"""Spot-check the Data API against the public leaderboard at openrouter.ai/rankings.

Usage: python scripts/spotcheck_rankings.py 2026-10-19
The date is the page's "Usage data through" date. One keyed call pulls the trailing 30 days ending
then; the script rebuilds the page's Today / This Week / This Month top-10 lists and compares them
with docs/spotcheck/rankings_page_<date>.csv (transcribed from the page). Writes docs/spotcheck/RESULT_<date>.md.
"""

import datetime as dt
import glob
import json
import os
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from pull import BASE, save  # noqa: E402  same saving and logging rules as the main pull


def names():
    """permaslug -> display name, from the newest model-list snapshot that lists it."""
    out = {}
    files = sorted(glob.glob(str(ROOT / "data/raw/models_wayback/*.json"))) + sorted(glob.glob(str(ROOT / "data/raw/models/*.json")))
    for f in files:  # oldest first, so newer names overwrite
        for m in json.load(open(f))["response"]["data"]:
            c, mid = m.get("canonical_slug"), m["id"]
            key = f"{c}:{mid.split(':', 1)[1]}" if c and ":" in mid and ":" not in c else (c or mid)
            n = m.get("name") or mid
            out[key] = n.split(": ", 1)[1] if ": " in n else n
            out.setdefault(mid, out[key])
    return out


def shown(x):
    """Format tokens the way the page does: 3 significant figures, T or B."""
    unit, div = ("T", 1e12) if x >= 1e12 else ("B", 1e9)
    return f"{x / div:.3g}{unit}"


def main():
    end = dt.date.fromisoformat(sys.argv[1])
    start = end - dt.timedelta(days=29)
    rel = f"spotcheck/rankings_daily_{start}_{end}.json"
    if not (ROOT / "data/raw" / rel).exists():
        load_dotenv(ROOT / ".env")
        key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not key:
            sys.exit("STOP: OPENROUTER_API_KEY is empty")
        params = {"start_date": str(start), "end_date": str(end)}
        r = requests.get(BASE + "/datasets/rankings-daily", params=params,
                         headers={"Authorization": f"Bearer {key}"}, timeout=60)
        if r.status_code != 200:
            sys.exit(f"STOP: {r.status_code}: {r.text[:300]}")
        save(rel, "/datasets/rankings-daily", params, r)
    resp = json.load(open(ROOT / "data/raw" / rel))["response"]
    d = pd.DataFrame(resp["data"])
    d["tokens"] = d["total_tokens"].astype("int64")
    d = d[d.model_permaslug != "other"]
    nm = names()
    page = pd.read_csv(ROOT / f"docs/spotcheck/rankings_page_{end}.csv")
    windows = {"today": end, "week": end - dt.timedelta(days=6), "month": start}
    lines = [f"# Spot-check vs openrouter.ai/rankings ({end})", "",
             f"API pull: `{rel}`, meta.as_of {resp['meta']['as_of']}.", "",
             "| Window | Rank | Page model | Page tokens | API model (slug) | API tokens | Match |", "|---|---|---|---|---|---|---|"]
    ok_all = 0
    for w, d0 in windows.items():
        x = d[d.date >= str(d0)].groupby("model_permaslug")["tokens"].sum().sort_values(ascending=False).head(10)
        p = page[page.window == w].sort_values("rank")
        for (slug, tok), row in zip(x.items(), p.itertuples()):
            api_name = nm.get(slug, slug)
            ok = api_name.lower() == row.model.lower() and shown(tok) == row.tokens_shown
            ok_all += ok
            lines.append(f"| {w} | {row.rank} | {row.model} | {row.tokens_shown} | {api_name} (`{slug}`) | {shown(tok)} | {'PASS' if ok else 'FAIL'} |")
    lines += ["", f"**{ok_all} of {len(page)} rows match on both model and rounded tokens.**"]
    out = ROOT / f"docs/spotcheck/RESULT_{end}.md"
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text())


if __name__ == "__main__":
    main()
