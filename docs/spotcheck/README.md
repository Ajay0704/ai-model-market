# Spot-check against openrouter.ai/rankings

`rankings_page_2026-10-19.csv` holds the page's Today / This Week / This Month top-10 tables, transcribed from openrouter.ai/rankings on 2026-10-19. The page said "Usage data through Oct 19, 2026". Per the page's methodology, Today, This Week and This Month are trailing 1, 7 and 30 days ending with the newest complete UTC day.

`scripts/spotcheck_rankings.py` pulls the same 30 days from the Data API (one call) and rebuilds the three lists. It checks that each model's rank matches and that its tokens round to the figure the page shows.

Source: OpenRouter (openrouter.ai/rankings), as of 2026-10-19. Licensed under CC BY 4.0.
