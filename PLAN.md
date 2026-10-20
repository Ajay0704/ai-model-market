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
- [ ] **5. Build.** Ajay's requirement (2026-10-19): the charts must look like a tech company made them.
  - [x] **5a. Style guide and mockup.** Done 2026-10-19, **awaiting Ajay's approval**.
    - `docs/STYLE_GUIDE.md` sources each rule to IBM Carbon, GitLab Pajamas (charts and dashboards) or Atlassian, and records the palette validator results.
    - `mockup/` holds a five-page HTML mockup with verified numbers. `analysis/export_mockup_data.py` writes `mockup/data.json`, and `mockup/build_mockup.py` inlines it. Published (private): https://claude.ai/artifact/Uwbgi7ZNMq6qfm9cQVxQvm
  - [x] **5b. Tableau Story.** Built 2026-10-19 and awaiting Ajay's visual check.
    - `tableau/make_workbook.py` (with `tableau/tableau_xml.py`, extended from the Olist helper) writes `tableau/AI_Model_Market.twbx`: 13 sheets, 5 dashboards and a 5-point story, using the style-guide palette, Tableau Book/Semibold fonts, hairline gridlines and card zones.
    - Data: `analysis/export_tableau_data.py` writes `tableau/data/*.csv` from the same `mockup/data.json`.
    - Verified through Tableau Desktop's own log: the workbook, sheets, dashboards and story parse, and the opening pages' queries run with 0 issues. One manual-sort error was found and fixed.
    - Not verifiable without a screen: the log-scale x-axis on "Quality vs price" (`scale='log'` isn't in any sample workbook) and overall visual polish.
    - Next: Ajay's look, then publish to Tableau Public (needs his sign-in).
  - [x] **5c. Power BI report.** Live 2026-10-19 in Ajay's My workspace: semantic model "AI Model Market" (6922d090-...) and report (1eae3240-...).
    - Built as code, the Olist way: `powerbi/gen_tmdl.py` (15 tables, 6 relationships, 23 DAX measures; typed M partitions read this public repo's CSVs anonymously, so no gateway) and `powerbi/gen_report.py` (PBIR, 5 pages, 43 visuals, published with `publish_report.js` through the Fabric REST API).
    - **The live DAX matches the pandas answer key 22/22** (`docs/POWERBI_RECONCILIATION.md`).
    - Fixed on the way: a measure named like a column (DAX is case-insensitive); Power BI's real property names for the log axis (`logAxisScale`) and the small-multiples grid (`smallMultiplesLayout`), read back from the editor; web-font stacks (a bare "Segoe UI" fell back to serif); never redefining a date column (it breaks the auto date table), so patches add columns only.
- [ ] **6. Verify, then deliverables.** Every number in both tools matches the answer key. Then the case-study PDF (Olist playbook format), a portfolio page and a résumé bullet. The README states plainly how AI assisted the build.

Rules: every published number carries "Source: OpenRouter (openrouter.ai/rankings), as of <date>"; the key lives only in this repo's `.env`; the pull stops at the first error and never saves an error as data.
