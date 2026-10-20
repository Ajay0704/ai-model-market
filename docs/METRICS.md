# Metric dictionary

Each metric is defined once here and computed once in `sql/`. Tableau and Power BI reuse these columns; they never re-derive a metric their own way. The Olist rule: most dashboard arguments are two people defining the same metric differently.

## Grain and keys
| Table | Grain | Key |
|---|---|---|
| `fct_model_day` | one model on one day (the top 50 + one `other` row) | `date`, `model_permaslug` |
| `fct_price_month` | one model in one month | `month`, `model_permaslug` |
| `dim_model` | one model slug | `model_permaslug` |
| `dim_lab` | one organization | `org_name` |
| `dim_date` | one calendar day | `date` |
| `mart_*` | as named (model-month, lab-month, family-week, ...) | see `sql/03_marts.sql` |

## Entities
| Term | Definition | Decision behind it |
|---|---|---|
| Model slug | `model_permaslug` exactly as OpenRouter reports it | Versions and `:free` variants stay separate here |
| Model family | Slug without its `:variant` and without a trailing `-YYYYMMDD` | Rolls `deepseek-v4-flash-20260423` and `-20260731` into one family |
| Organization (lab) | The organization behind the slug prefix, from `data/reference/labs.csv` (one first-party source per row) | `meta` and `meta-llama` both map to Meta; `qwen` and `alibaba` to Alibaba |
| Country group | US, China, Europe, Rest of world, from the organization's stated HQ | It's the developer's HQ, not where the model is hosted or what base model it was tuned from |
| Stealth | Slugs under `stealth/` or `openrouter/` (unnamed pre-release models) | Its own group; never credited to a lab by guesswork |
| Long tail | The daily `other` row: every model outside that day's top 50 | Its own group; included in every denominator |
| Open weights | OpenRouter links the model to a Hugging Face repo (`hugging_face_id`) | Unknown (blank) when no snapshot carried the field |

## Metrics
| Metric | Definition | Decision behind it |
|---|---|---|
| Tokens | `prompt_tokens + completion_tokens`, as OpenRouter reports it | No input/output split is available per model |
| Token share | Tokens / **all** tokens that period (including the long tail) | A share of named tokens would inflate every lab |
| Avg tokens per day | Tokens in the month / days with data in that month | 2 days are missing; a sum would fake a dip |
| Blended price ($/M) | 1e6 x (15/16 x input price + 1/16 x output price), from the snapshot closest to mid-month | 15:1 follows OpenRouter's own study (about 6K prompt vs 400 completion tokens per request) |
| Blended price, 3:1 | Same, with Artificial Analysis's 3:1 convention | Sensitivity check only |
| Estimated spend | Tokens x blended price | List price before caching discounts, BYOK and negotiated rates, so an **upper bound**. Use for **shares, not dollar totals** |
| Spend share | Estimated spend / estimated spend of all priced tokens that month | The long tail has no price, so it can't enter this denominator |
| Average price paid ($/M) | Estimated spend / priced tokens that month (token-weighted blended price) | How the price of the typical token moves, not the price of a typical model |
| Open-weight share | Tokens from models with open weights / **all** tokens that period | Stealth, the long tail and unknown-status models stay in the denominator, so this is a floor |
| Free-variant share | Tokens on `:free` slugs / all tokens | Free variants are separate slugs, so this is exact |
| HHI | 10,000 x sum of squared shares of named tokens (families, or labs) | The `other` row is many models, so it's excluded. Reference line: the DOJ/FTC 2023 Merger Guidelines call a market above 1,800 "highly concentrated" (a benchmark for reading the number, not a legal claim) |
| Top-5 family share | Tokens of the 5 largest families / all tokens | Shares of all tokens, so it can't exceed reality |
| Launch week | The first day a family enters the top 50, for families first seen on or after 2025-02-01 | Families already there on 2025-01-01 have unknown launch dates |
| Launch curve | A family's average share of each day's tokens, by week since launch (weeks 0-25) | Days outside the top 50 count as 0 share (the model is in the long tail) |
| Quality vs price | Artificial Analysis Intelligence Index vs blended price, bubble = tokens in the last 90 days | Benchmarks are a snapshot, so usage is restricted to recent months |
| Category mix | A category's tokens per organization / that category's total, per month | Sampled estimates; use as mix shares only |

## Attribution (on every page)
"Source: OpenRouter (openrouter.ai/rankings), as of 2026-10-19. Licensed under CC BY 4.0." The quality chart adds "Benchmarks: Artificial Analysis (artificialanalysis.ai) via OpenRouter."
