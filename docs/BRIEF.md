# Brief: The AI Model Market, who's winning?

## The business
[OpenRouter](https://openrouter.ai) is a marketplace for AI models. Apps send requests through one API, and OpenRouter routes each one to a model from one of many labs. Its public model list had 470 models on 2026-10-19.

It is a two-sided marketplace, so the Olist playbook carries over:

| Olist | OpenRouter |
|---|---|
| Sellers | Model labs (OpenAI, Anthropic, Google, DeepSeek, Qwen, ...) |
| Customers | Apps that call the API |
| GMV | Tokens processed |
| Product categories | Task types (coding, roleplay, ...) |
| Price | Price per million tokens |

## Stakeholders and the decision each one owns
These stakeholders and questions are my own design. They are grounded in 221 analyst postings from 58 tech companies (Ajay's job-scan archives, Oct 9-19 2026); see "Why this project" below.

| Stakeholder | Decision they own | Question the dashboard must answer |
|---|---|---|
| Leadership / strategy | Which labs to partner with or bet on | Who is winning tokens, and is the market concentrating or spreading out? |
| Pricing / finance | How to price, and where the money is | Does the cheapest model win? How does a lab's share of tokens compare with its estimated share of spend? |
| AI platform team | Which model to route each workload to | Which models give the best quality for the price? |
| Competitive intelligence | Where the threats come from | Are open-weight models and Chinese labs gaining on closed US models? |
| Product / GTM | Launch planning, and which apps and tasks to court | Do new models keep their usage after launch? Which apps and tasks drive demand? |

## Hypotheses to test (not findings)
| # | Hypothesis | Why it's worth testing |
|---|---|---|
| H1 | Chinese models now take the largest share of OpenRouter tokens | Third-party trackers claim 45-61% in 2026, with figures that disagree; the a16z x OpenRouter study found Chinese open models averaged about 13% weekly share in 2025 |
| H2 | Token share and spend share tell different stories | Menlo Ventures' late-2025 enterprise survey has Anthropic 40% / OpenAI 27% / Google 21% of enterprise LLM API spend |
| H3 | Cheap and free models win volume, but the top-quality models win spend | Price per token is falling fast (secondary sources disagree on how fast) |
| H4 | New models peak within weeks of launch, then fade | The "launch cohort" view is the marketplace version of Olist's retention heatmap |
| H5 | The market is spreading out, not concentrating | The top-5 model share and an HHI index over time test it directly |
| H6 | The highest-scoring model is not the most used | Benchmark score vs price vs usage |

## Caveats that go into the story, not a footnote
- **OpenRouter is not the whole market.** It sees only its own traffic. Apps that call OpenAI or Anthropic directly are invisible. Every claim says "on OpenRouter".
- **Top 50 models per day only**, plus one "other" row.
- **Stealth models.** Some top models are unnamed pre-release models. They get their own "stealth" label.
- **Restatements.** OpenRouter says figures may be restated as data refreshes, so every pull stores its `meta.as_of`.
- **Prices are current-only.** The model list has no price history, so estimated spend uses today's price.

## Why this project (evidence from job postings)
Coded from 221 analyst-titled postings at 58 tech companies, with company boilerplate removed:
- 43% ask analysts to use AI tools in the work; 11% name Claude Code, Copilot, Cursor or Codex.
- 15% ask analysts to analyze AI itself: product usage, AI cost, or model evaluation.
- Tools: SQL 50%, Python 35%, Tableau 25%, Power BI 8%, Looker 4%.

## Sources
- OpenRouter Data API: https://openrouter.ai/docs/cookbook/administration/data-api (CC BY 4.0, attribution required)
- OpenRouter rankings: https://openrouter.ai/rankings
- State of AI, an empirical 100 trillion token study with OpenRouter (a16z): https://arxiv.org/html/2601.10088v1
- Menlo Ventures 2025 report, as covered by BigDATAwire: https://www.hpcwire.com/bigdatawire/this-just-in/menlo-ventures-report-enterprise-llm-spend-reaches-8-4b-as-anthropic-overtakes-openai/
- Third-party share estimates (to verify, not to cite as fact): https://www.trendingtopics.eu/chinese-ai-models-overtake-us-rivals-in-global-token-consumption/
