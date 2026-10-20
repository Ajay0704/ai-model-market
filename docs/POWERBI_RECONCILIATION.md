# Power BI reconciliation

DAX run: 2026-10-19, semantic model 6922d090-0624-428c-aeda-22f0399d64ea, after a full refresh from GitHub. Key: `scripts/answer_key.py` (pandas on the raw pulls).
A row passes when the two agree to 9 significant digits.

| # | Check | DAX measure | Live model (DAX) | Answer key | Match |
|---|---|---|---|---|---|
| 01 | Total tokens, all days | `[Total Tokens]` | 2.3681873e+15 | 2.3681873e+15 | PASS |
| 02 | Tokens, Jan 2025 | `[Total Tokens]` | 2.23013396e+12 | 2.23013396e+12 | PASS |
| 03 | Tokens, Sep 2026 | `[Total Tokens]` | 5.75897453e+14 | 5.75897453e+14 | PASS |
| 04 | Tokens per day, Sep 2026 (T) | `[Tokens per Day (T)]` | 19.1965818 | 19.1965818 | PASS |
| 05 | China token share, Jan 2025 | `[China Token Share]` | 0.0598754936 | 0.0598754936 | PASS |
| 06 | China token share, Jan 2026 | `[China Token Share]` | 0.227750376 | 0.227750376 | PASS |
| 07 | China token share, Sep 2026 | `[China Token Share]` | 0.585139224 | 0.585139224 | PASS |
| 08 | US token share, Jan 2025 | `[US Token Share]` | 0.81136444 | 0.81136444 | PASS |
| 09 | US token share, Jan 2026 | `[US Token Share]` | 0.647953395 | 0.647953395 | PASS |
| 10 | US token share, Sep 2026 | `[US Token Share]` | 0.288706672 | 0.288706672 | PASS |
| 11 | Lab HHI, Jan 2025 | `[Lab HHI]` | 3,072.36485 | 3,072.36485 | PASS |
| 12 | Lab HHI, Sep 2026 | `[Lab HHI]` | 1,355.53435 | 1,355.53435 | PASS |
| 13 | China spend share, Jan 2025 | `[China Spend Share]` | 0.0120722789 | 0.0120722789 | PASS |
| 14 | China spend share, Sep 2026 | `[China Spend Share]` | 0.396799619 | 0.396799619 | PASS |
| 15 | US spend share, Jan 2025 | `[US Spend Share]` | 0.978493376 | 0.978493376 | PASS |
| 16 | US spend share, Sep 2026 | `[US Spend Share]` | 0.602533798 | 0.602533798 | PASS |
| 17 | Average price paid $/M, Jan 2025 | `[Avg Price Paid]` | 2.02594424 | 2.02594424 | PASS |
| 18 | Average price paid $/M, Sep 2026 | `[Avg Price Paid]` | 0.677461139 | 0.677461139 | PASS |
| 19 | China token share, Sep 2026 (monthly fact) | `[Token Share Sep 2026]` | 0.585139224 | 0.585139224 | PASS |
| 20 | China spend share, Sep 2026 (chart measure) | `[Spend Share Sep 2026]` | 0.396799619 | 0.396799619 | PASS |
| 21 | Partial month blanked in the HHI chart | `[Lab HHI (full months)] for Oct 2026` | -1 | -1 | PASS |
| 22 | Daily fact rows | `COUNTROWS(fct_model_day)` | 33,354 | 33,354 | PASS |

**22 of 22 checks match.** (21: -1 means the measure correctly returns blank for the partial month.)
