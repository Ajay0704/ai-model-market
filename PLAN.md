# Plan

Approved by Ajay on 2026-10-19: both a Tableau Story and a Power BI report, like Olist.

- [x] **0. Repo.** `~/ai-model-market`, with `.env` gitignored, a venv, and this plan.
- [x] **1. Pull and profile.** Done 2026-10-19: all 51 Data API calls, the live model list, and 22 monthly Internet Archive snapshots of the model list (added for price history). See `docs/DATA_PROFILE.md` and `docs/DATA_DECISIONS.md`. About 30 calls (the limit is 500/day):
  - rankings-daily from 2025-01-01 (two 366-day windows)
  - the public model list
  - benchmarks (3 sources)
  - top 100 apps per month
  - the 7-day task mix

  Every response is saved whole, with its `meta`. Profiling covers: stealth models, renamed or versioned slugs, the "other" row, gaps in days.
- [x] **2. Model and metric dictionary.** Done 2026-10-19.
  - `scripts/build_model.py` + `sql/01_dims.sql`, `02_facts.sql`, `03_marts.sql` -> `data/processed/*.csv`: 4 base tables, monthly prices, 8 marts, and a flat Tableau table.
  - `docs/METRICS.md` is the metric dictionary.
  - `data/reference/labs.csv` maps 45 prefixes to 42 organizations, each with a source (44 first-party, 1 secondary).
  - `scripts/check_model.py` runs 15 integrity checks, all passing (`docs/MODEL_CHECKS.md`).
- [x] **3. Answer key.** Done 2026-10-19.
  - `scripts/answer_key.py` recomputes 42 headline numbers in pandas from the raw files only: **42/42 match** the DuckDB marts (`docs/ANSWER_KEY.md`). It caught one real bug, variant ids claiming the base model's price (`docs/DATA_DECISIONS.md` #9).
  - `scripts/spotcheck_rankings.py` against the public openrouter.ai/rankings page: **29/30** top-10 rows match on model and rounded tokens. The 1 miss is the documented top-50 cut (#10). The benchmark top 10 also matches.
- [x] **4. Explore.** Done 2026-10-19. All six hypotheses were tested with robustness cuts and the 3:1 blend (`analysis/explore_*.py`); verdicts are in `docs/FINDINGS.md`. Kept: H1 (China leads tokens since Apr 2026, robust to worst-case attribution; a tie by requests), H2 (the token vs spend gap, the central finding), H3 (cheap tokens, premium spend; the price decline is about 90% mix), H4 reframed as "models churn, labs retain", H5 with its Q3-2026 reversal, H6 (top scorers take 2% of tokens). Context only: 260x growth, coding's rise, open weights at 63%.
- [ ] **5. Build.** Ajay's requirement (2026-10-19): the charts must look like a tech company made them. So the build starts with a short style guide drawn from tech companies' own published data-viz design systems (cited), plus a mockup for his approval, before either tool is touched.
  - **Tableau Story**: one story point per stakeholder. The `.twbx` is generated in code with the `tableau_xml.py` approach from `~/olist-text2sql/scripts/`, then published to Tableau Public (like the SaaS Pricing viz).
  - **Power BI report**: one page per stakeholder, built in Power BI web (a Mac and a Free license, so no Desktop). As with the Olist report (`Ajay0704/ecommerce-powerbi`): the processed CSVs live in a public GitHub repo, and Power Query Online reads them over HTTPS, so refresh needs no gateway. The model is TMDL plus DAX measures applied in the TMDL view, as in `~/retail-margin-churn/powerbi/`. Creating the public GitHub repo needs Ajay's go first.
- [ ] **6. Verify, then deliverables.** Every number in both tools matches the answer key. Then the case-study PDF (Olist playbook format), a portfolio page and a résumé bullet. The README states plainly how AI assisted the build.

Rules: every published number carries "Source: OpenRouter (openrouter.ai/rankings), as of <date>"; the key lives only in this repo's `.env`; the pull stops at the first error and never saves an error as data.
