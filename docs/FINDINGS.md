# Findings: what survived step 4

Each hypothesis from `docs/BRIEF.md` was tested with several cuts of the data (`analysis/explore_h1_h2.py`, `analysis/explore_h3_h6.py`). A finding makes the story only if it passes the Olist tests:
- **Big:** it changes a number a stakeholder cares about.
- **Reliable:** it holds across cuts, including the 3:1 price blend, not just in one slice.
- **Actionable:** someone owns a decision it changes.

Every number below is from the model the answer key verified (`docs/ANSWER_KEY.md`). The data covers OpenRouter traffic only.

## Verdicts

| # | Hypothesis | What the data said | Cuts that held (and the ones that didn't) | Verdict |
|---|---|---|---|---|
| H1 | Chinese models now take the largest share of tokens | China first passed the US on weekly tokens the week of **2026-03-23**, and has led **every week since 2026-04-27** (the US last led the week of 2026-04-20). Sep 2026: **China 58.5%, US 28.9%** (Jan 2025: 6.0% vs 81.1%). Five Chinese labs each hold 2% or more, so it's not one lab. | Held in Jun and Sep 2026 under every cut: crediting all stealth and long-tail tokens to the US (58.5 vs 40.3), paid tokens only (60.5 vs 25.8), and without DeepSeek (47.2 vs 36.8). Programming tokens too (sampled, 56.5 vs 24.7). **Failed in Mar 2026 under every cut**, so the lead dates from Q2 2026, not Q1. **By requests, it's a tie:** the public page's week of Oct 12 has named Chinese labs at 44.3% and US labs at 45.0%, so Chinese models win on longer, token-heavy requests. | **Kept: the hook.** Say "tokens", never "usage" in general. |
| H2 | Token share and spend share tell different stories | Every month, China's share of estimated spend is far below its share of tokens. In 2026 the gap was never under 18.8 points. Sep 2026: **China 58.5% of tokens, 39.7% of spend; US 28.9% of tokens, 60.3% of spend.** Anthropic has 3.4% of tokens but 28.3% of spend ($5.19/M); DeepSeek has 21.5% of tokens but 5.3% of spend ($0.16/M). | Held every month and under the 3:1 blend (China 36.5%, US 63.5% of spend in Sep 2026). China's spend share swings from 4% to 40% across Jan-Sep 2026, so the **gap** is reliable but the **level** isn't. | **Kept: the central finding.** Headline the gap, not a spend level. |
| H3 | Cheap and free models win volume, but premium models win spend | Sep 2026: models under $0.25/M (including free) carry **59.7% of priced tokens but 6.2% of spend**; models at $1/M and up carry **13.9% of tokens but 69.8% of spend**. The average price paid fell **67%** ($2.03 to $0.68/M, Jan 2025 to Sep 2026). Over the same period, a same-model list-price index fell only **10%**. So about nine-tenths of the decline (in log terms) is **users moving to cheaper models**, not list-price cuts. | Tiers held under the 3:1 blend (59.7% of tokens / 6.0% of spend; $1+: 27.5% / 88.0%). The decline is not a straight line: the average price rose 53% from Nov 2025 to May 2026 before falling. | **Kept.** The price-vs-mix split is the analyst move. |
| H4 | New models peak within weeks, then fade | 103 notable launches (peaking at 1% or more of daily tokens, 13+ weeks observed, stealth models excluded). Median peak in **week 4**. By week 12 the median model keeps **21%** of its peak share, and **76%** fall below half. **But its lab keeps 70%** of its level, and only 31% of labs fall below half: users move to the same lab's next model. **US labs hold users far better:** model 33%, lab 72% (14% below half). China: model 11%, lab 49% (50% below half). (A lab that drops out of the top 50 counts as 0. An earlier version skipped those cases and overstated lab retention: 71% overall, 59% for China.) | Held for 2025 and 2026 launches, and for the largest launches (peak 5%+). Stealth models were excluded because they "die" when renamed at launch. | **Kept, reframed: "models churn, labs retain".** That's more actionable than the original hypothesis. |
| H5 | The market is spreading out, not concentrating | Lab HHI fell from **2,855 (Q1 2025) to 1,110 (Q2 2026)**, quarterly averages. By month, it first dipped below the 1,800 "highly concentrated" line in Aug 2025, went back above it Sep-Nov, and has been **below it every month since Dec 2025** (monthly low: 992 in Apr 2026). **But it rose again** to 1,248 in Q3 2026 (1,477 so far in Q4), and the top-5 model share went from 34% to 48%. | Same picture with stealth counted as its own lab. | **Kept with the reversal stated:** competitive, but re-concentrating since Q3 2026. |
| H6 | The highest-scoring model is not the most used | Across 72 benchmarked models with usage, rank correlation between Intelligence Index and tokens is **0.19** (weak). The **5 highest scorers (52.7-57.6) take 2.0%** of the last 90 days' tokens; the **5 most-used (scores 24.4-41.8) take 32.5%**. Only 7 of 91 scored models sit on the price-quality frontier, carrying 13.2% of scored usage. | The frontier set and its share are identical under the 3:1 blend. | **Kept.** Frame it as routing, not a market ignoring quality (see caveats). |

## Context only (true, but no decision hangs on it alone)
- **Volume grew about 260x** (2.2T to 575.9T tokens a month, Jan 2025 to Sep 2026). It's the opening number, not a finding.
- **Coding took over:** programming went from 18.4% of categorized tokens (May 2025) to 58.6% (Sep 2026), and roleplay fell from 17.6% to 5.8%. It swings (35.6% in Jan 2026), and categories are sampled. The top apps are coding agents (Hermes Agent, Kilo Code, Claude Code, Cline).
- **Open weights carry 63% of tokens** (Sep 2026). It overlaps H1, since most Chinese models are open-weight.

## Guarding against over-claiming (written into the story, not hidden)
- **OpenRouter is not the market.** Direct API traffic to OpenAI, Anthropic or Google is invisible here. Menlo Ventures' late-2025 enterprise survey puts Anthropic at 40% of enterprise LLM API spend. Two different markets, both real.
- **Tokens are not requests, and requests are not users.** H1 holds on tokens; by requests it's a tie for the one week the public page shows.
- **Estimated spend is list price before caching discounts**, so it's an upper bound. It's used for shares only.
- **H6 is about routing, not taste.** Benchmarks score one setting per slug (e.g. "Max"), while usage covers every setting. Bulk tasks like classification may rationally use cheap models: in the 7-day task snapshot, classification is the largest task by usage share.
- **H4's lab retention is measured from the model's peak week**, so it includes the launch spike in the base.

## How the findings map to the story (input to step 5)
| Stakeholder page | Finding | Chart job |
|---|---|---|
| Leadership | H1 + growth context + H5 | Share over time (stacked area by country group), with the crossover week marked |
| Pricing / finance | H2 + H3 | Tokens vs spend side by side, by country and lab; price-vs-mix line pair |
| AI platform team | H6 | Price-quality scatter with the frontier, bubble = usage |
| Competitive intel | H1 cuts + breadth | Chinese labs' shares (small multiples); the robustness table |
| Product / GTM | H4 + coding context | Launch curves (model vs lab retention, US vs China); category mix over time |
