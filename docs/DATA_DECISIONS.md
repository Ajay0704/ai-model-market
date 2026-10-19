# What the data profile decided

Each finding comes from `docs/DATA_PROFILE.md` (regenerate it with `python scripts/profile.py`). Each one changes how a later step works, the same way Olist's partial months and customer-id trap did.

| # | Finding | Decision |
|---|---|---|
| 1 | **Explosive growth.** Monthly tokens went from 2.2T (Jan 2025) to 575.9T (Sep 2026), about 260x. An "all-time share" is really just the last few months. | Show shares **per month** (or per week). Never headline an all-time share. Growth gets its own chart. |
| 2 | **Two missing days** (2025-06-15 and 2025-07-15). | Leave them as gaps, never zeros. Monthly volume is shown as **average tokens per day**, so a missing day can't fake a dip. Shares are unaffected. |
| 3 | **The same model appears under many slugs.** Of 436 slugs, 166 carry a release-date suffix (e.g. `deepseek-v4-flash-20260423` and `-20260731`), and 80 are `:free` variants. | Derive three levels: `model_permaslug` (as given), `model_family` (date suffix and `:variant` stripped) and `lab` (the prefix, with aliases merged, e.g. `meta-llama` and `meta` become Meta). Free variants get an `is_free` flag. |
| 4 | **Unattributable tokens.** The `other` row (outside each day's top 50) is 6.6% of all tokens. Stealth and OpenRouter house models are 4.8% of named tokens. | Lab share uses **all tokens** as the denominator. "Long tail (outside top 50)" and "Stealth (unnamed lab)" appear as their own groups, never silently dropped or guessed. |
| 5 | **Prices change and models retire.** Today's list covers only 88.2% of named tokens. Adding 22 monthly Internet Archive snapshots of the same list raises that to 97.7%. | Price each model-month from the **snapshot nearest that month**. Estimated spend = tokens x a blended price, labeled an estimate. The rankings give total tokens only, so the input/output split is an assumption, written into the metric dictionary. |
| 6 | **Category data is sampled, and edge buckets are partial.** Each yearly pull also returned a partial bucket for the month before its start date (about 12% of the real month). The 12 categories sum to 85-91% of total tokens. Category history starts May 2025. | Keep only months inside each pull's own window (12 edge buckets dropped). Use categories as **mix shares**, not totals. Category charts start May 2025. |
| 7 | **Benchmarks are a snapshot**, not history. Artificial Analysis covers 69% of the last 90 days' named tokens; Design Arena only 16%. | The quality-vs-price chart uses the **last 90 days**, Artificial Analysis's intelligence index, and states its coverage on the chart. Design Arena is left out. |
| 8 | **The task mix is a 7-day snapshot** only. | It's used as a "this week" panel. Task history comes from the monthly categories (finding 6). |

## Storage
- `data/raw/models_wayback/` (9.7 MB) is gitignored. It can be rebuilt any time with `scripts/pull_wayback_models.py`.
- What gets republished in a public repo (for Power BI's web refresh) is decided before that repo is created. By default it's the processed tables only, each with the OpenRouter attribution.
