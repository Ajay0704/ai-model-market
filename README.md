# The AI Model Market: who's winning?

A Tableau Story and a Power BI report on which AI models and labs win usage on OpenRouter, the largest public marketplace for AI models. Built from OpenRouter's public Data API (daily data from January 2025).

Status: in progress. See [PLAN.md](PLAN.md) and the [brief](docs/BRIEF.md).

## Setup
```bash
uv venv .venv && uv pip install -p .venv/bin/python -r requirements.txt
cp .env.example .env   # then paste your own OpenRouter key into .env
.venv/bin/python scripts/pull.py models       # public, no key
.venv/bin/python scripts/pull.py all          # needs the key
.venv/bin/python scripts/pull_wayback_models.py  # monthly price history
.venv/bin/python scripts/profile.py           # writes docs/DATA_PROFILE.md
```

## Data and license
Source: OpenRouter (openrouter.ai/rankings). The data is licensed under CC BY 4.0. Each published number is marked with the `as_of` date of the pull it came from.
