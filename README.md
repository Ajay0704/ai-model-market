# The AI Model Market: who's winning?

A Tableau Story and a Power BI report on which AI models and labs win usage on OpenRouter, the largest public marketplace for AI models. Built from OpenRouter's public Data API (daily data from January 2025).

Status: Tableau Story built (`tableau/AI_Model_Market.twbx`); Power BI report live, with its DAX reconciled 22/22 to the answer key. Case study and portfolio page next. See [PLAN.md](PLAN.md), the [brief](docs/BRIEF.md) and the [metric dictionary](docs/METRICS.md).

## How it's built
```
OpenRouter Data API + Internet Archive model-list snapshots
  -> data/raw/ (whole responses, with as_of)
  -> scripts/build_model.py: staging tables in DuckDB
  -> sql/01_dims.sql, 02_facts.sql, 03_marts.sql
  -> data/processed/*.csv -> Tableau Story + Power BI report
```

## Setup
```bash
uv venv .venv && uv pip install -p .venv/bin/python -r requirements.txt
cp .env.example .env   # then paste your own OpenRouter key into .env
.venv/bin/python scripts/pull.py models       # public, no key
.venv/bin/python scripts/pull.py all          # needs the key
.venv/bin/python scripts/pull_wayback_models.py  # monthly price history
.venv/bin/python scripts/profile.py           # writes docs/DATA_PROFILE.md
.venv/bin/python scripts/build_model.py       # DuckDB model -> data/processed/*.csv
.venv/bin/python scripts/check_model.py       # writes docs/MODEL_CHECKS.md, fails on any broken check
.venv/bin/python scripts/answer_key.py        # independent pandas recompute, writes docs/ANSWER_KEY.md
.venv/bin/python scripts/spotcheck_rankings.py 2026-10-19  # vs the public rankings page
.venv/bin/python analysis/export_mockup_data.py   # verified numbers -> mockup/data.json
.venv/bin/python mockup/build_mockup.py           # HTML mockup
.venv/bin/python analysis/export_tableau_data.py  # -> tableau/data/*.csv
.venv/bin/python tableau/make_workbook.py         # -> tableau/AI_Model_Market.twbx
```

## Data and license
Source: OpenRouter (openrouter.ai/rankings). The data is licensed under CC BY 4.0. Each published number is marked with the `as_of` date of the pull it came from.

## Power BI (as code)
- `powerbi/measures.dax` holds every measure. `gen_tmdl.py` writes `model_full.tmdl` (tables with typed M partitions that read this repo's CSVs from GitHub, plus relationships and measures); paste it into Power BI web's TMDL view.
- `gen_report.py` writes the PBIR report (theme from `docs/STYLE_GUIDE.md`). `publish_report.js` creates or updates it through the Fabric REST API from a signed-in app.powerbi.com tab.
- `reconcile.py` compares the live model's DAX with the pandas answer key: `docs/POWERBI_RECONCILIATION.md` (22/22).
