"""Pull OpenRouter Data API responses into data/raw/, saved whole with their meta.

Usage:
  python scripts/pull.py models                 # public model list, no key needed
  python scripts/pull.py all [--dry-run]        # every keyed dataset below
  python scripts/pull.py rankings|categories|apps|benchmarks|tasks [--force]

Rules (the key is this project's own; never another project's):
  - at most --max-calls keyed calls per run (default 80; OpenRouter allows 500/day)
  - about 2.2 s between keyed calls, under the 30 requests/minute limit
  - stop at the first non-200 response, and never save an error as data
  - a file that already exists is skipped unless --force
"""

import argparse
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
LOG = RAW / "_pull_log.jsonl"
BASE = "https://openrouter.ai/api/v1"
FIRST_DAY = dt.date(2025, 1, 1)  # earliest date the Datasets API serves
CATEGORIES = ["programming", "roleplay", "marketing", "marketing/seo", "technology", "science",
              "translation", "legal", "finance", "health", "trivia", "academia"]
BENCH_SOURCES = ["artificial-analysis", "design-arena", "openrouter"]
PAUSE = 2.2


def last_complete_month(today):
    return today.replace(day=1) - dt.timedelta(days=1)


def month_windows(start, end):
    """(first_day, last_day) for every whole month from start's month through end's month."""
    out, d = [], start.replace(day=1)
    while d <= end:
        nxt = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        out.append((d, nxt - dt.timedelta(days=1)))
        d = nxt
    return out


def year_windows(start, end):
    """Calendar-year windows, each within the API's 366-day maximum span."""
    out, y = [], start.year
    while y <= end.year:
        a, b = max(start, dt.date(y, 1, 1)), min(end, dt.date(y, 12, 31))
        out.append((a, b))
        y += 1
    return out


def plan(kind, today):
    """Return a list of (relative_path, endpoint, params) for one dataset kind."""
    yesterday = today - dt.timedelta(days=1)
    lcm = last_complete_month(today)
    calls = []
    if kind == "rankings":
        for a, b in year_windows(FIRST_DAY, yesterday):
            calls.append((f"rankings_daily/{a}_{b}.json", "/datasets/rankings-daily",
                          {"start_date": str(a), "end_date": str(b)}))
    elif kind == "categories":
        for cat in CATEGORIES:
            for a, b in year_windows(FIRST_DAY, lcm):
                calls.append((f"rankings_category_month/{cat.replace('/', '-')}_{a}_{b}.json",
                              "/datasets/rankings-daily",
                              {"start_date": str(a), "end_date": str(b), "period": "month", "category": cat}))
    elif kind == "apps":
        for a, b in month_windows(FIRST_DAY, lcm):
            calls.append((f"app_rankings_month/{a:%Y-%m}.json", "/datasets/app-rankings",
                          {"start_date": str(a), "end_date": str(b), "sort": "popular", "limit": 100, "offset": 0}))
    elif kind == "benchmarks":
        for src in BENCH_SOURCES:
            calls.append((f"benchmarks/{src}_{today}.json", "/benchmarks", {"source": src, "max_results": 100}))
    elif kind == "tasks":
        calls.append((f"task_classifications/7d_{today}.json", "/classifications/task", {"window": "7d"}))
    else:
        raise SystemExit(f"unknown kind: {kind}")
    return calls


def log(entry):
    with LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def fetch(endpoint, params, key):
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    r = requests.get(BASE + endpoint, params=params, headers=headers, timeout=60)
    return r


def save(rel, endpoint, params, r):
    body = r.json()
    path = RAW / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"request": {"url": BASE + endpoint, "params": params,
                          "pulled_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")},
              "response": body}
    path.write_text(json.dumps(record, indent=1))
    data = body.get("data")
    rows = len(data) if isinstance(data, list) else None
    as_of = (body.get("meta") or {}).get("as_of")
    log({**record["request"], "status": r.status_code, "rows": rows, "as_of": as_of, "file": rel})
    return rows, as_of


def pull_models(force):
    rel = f"models/models_{dt.date.today()}.json"
    if (RAW / rel).exists() and not force:
        print(f"skip {rel} (exists)")
        return
    r = fetch("/models", {}, None)
    if r.status_code != 200:
        sys.exit(f"STOP: /models returned {r.status_code}: {r.text[:300]}")
    rows, _ = save(rel, "/models", {}, r)
    print(f"saved {rel}: {rows} models")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["models", "rankings", "categories", "apps", "benchmarks", "tasks", "all"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--max-calls", type=int, default=80)
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)

    if a.kind == "models":
        return pull_models(a.force)

    today = dt.datetime.now(dt.timezone.utc).date()
    kinds = ["rankings", "categories", "apps", "benchmarks", "tasks"] if a.kind == "all" else [a.kind]
    calls = [c for k in kinds for c in plan(k, today)]
    todo = [c for c in calls if a.force or not (RAW / c[0]).exists()]
    print(f"{len(calls)} planned, {len(todo)} to fetch (cap {a.max_calls})")
    if a.dry_run:
        for rel, ep, p in todo:
            print(f"  {ep} {p} -> {rel}")
        return
    if len(todo) > a.max_calls:
        sys.exit(f"STOP: {len(todo)} calls is over the cap of {a.max_calls}; raise --max-calls deliberately")

    load_dotenv(ROOT / ".env")
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        sys.exit("STOP: OPENROUTER_API_KEY is empty. Put your own key in .env (see .env.example).")

    for i, (rel, ep, p) in enumerate(todo, 1):
        if i > 1:
            time.sleep(PAUSE)
        r = fetch(ep, p, key)
        if r.status_code != 200:
            log({"url": BASE + ep, "params": p, "status": r.status_code, "file": None,
                 "error": r.text[:300], "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
            sys.exit(f"STOP at call {i}/{len(todo)}: {ep} {p} returned {r.status_code}: {r.text[:300]}")
        rows, as_of = save(rel, ep, p, r)
        print(f"[{i}/{len(todo)}] {rel}: {rows} rows, as_of {as_of}")


if __name__ == "__main__":
    main()
