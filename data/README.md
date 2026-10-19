# Data

`raw/` holds OpenRouter Data API responses, saved whole: `{"request": {...}, "response": {...}}`. Each response keeps its `meta` (`as_of`, `version`, resolved dates) because OpenRouter may restate figures later. `raw/_pull_log.jsonl` records every call made.

`processed/` holds the modeled tables the dashboards read (built in step 2).

Source: OpenRouter (openrouter.ai/rankings). The data is licensed under CC BY 4.0.
