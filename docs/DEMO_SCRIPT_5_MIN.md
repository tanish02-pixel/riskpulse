# Live demo script - maximum five minutes

## Before the jury

Run the app on your own laptop. Complete the FinBERT setup once, restart, and confirm the active model says `finbert`. Inspect all dashboard pages manually. Keep the terminal open. Prepare the seven-slide PDF, repository link, and application. Disable unrelated notifications. Use fictional examples only in Synthetic replay. A fresh/reset replay gives a clear 10% starting baseline.

## Timed flow

| Time | Show | Say |
|---|---|---|
| 0:00-0:25 | Title and app Overview | "RiskPulse implements the required risk engine and Module A, a sentiment-driven ten-stock mock index." |
| 0:25-1:05 | Data sources, Live feeds, Refresh sources | "BBC supplies financial news. Apple and Microsoft supply company announcements. We preserve source and publication time. The status reports errors honestly." |
| 1:05-1:40 | Risk signals, open a live record | "The engine produces sentiment, event classification and impact. Here are the source text and actual backend. Impact is a rule-based severity proxy." |
| 1:40-2:35 | Switch to Synthetic replay, Run scenario, Index allocation | "These are clearly labeled fictional events. Positive and negative company signals change the ten-stock targets. Baseline is 10% each and weights sum to 100%." |
| 2:35-3:15 | Allocation chart and weight history | "Freshness and confidence affect the tilt. We enforce a 2% floor, 18% cap and 10% normal one-way turnover. SQLite saves each changed allocation." |
| 3:15-3:50 | Open a negative replay signal | "FinBERT estimates tone. Event phrases and severity cues remain inspectable. Global and ambiguous shared-company signals cannot tilt a company weight." |
| 3:50-4:20 | Policy settings and active backend | "These policy settings are configurable and persisted. The interface identifies a fallback if the model is unavailable." |
| 4:20-4:45 | JSON export or /docs | "The same structured signals are available through the API or a file for other applications." |
| 4:45-5:00 | Validation slide | "28 implementation tests passed. A small 24-case synthetic check matched labels. Real-news validation and backtesting are future work." |

If live fetch takes too long or fails, show its status and continue with the explicitly labeled replay. Do not describe replay as real-time news. If the model says `financial_lexicon`, identify that backend and do not claim FinBERT is active.

## Useful optional text preview

Paste `Synthetic: Apple reports record profit and raises earnings guidance.` into Analyse text. Preview without saving. For a negative example, use `Synthetic: JPMorgan faces a credit downgrade after a missed repayment.` Keep manual demonstrations in the replay workspace.

## Q&A preparation

Review `ARCHITECTURE.md`, `EXPLANATION_HINGLISH.md`, `DATA_SOURCES.md`, and `AI_USAGE.md`. Explain why headline/summary analysis and phrase rules need a richer real-news benchmark. Explain why sentiment does not predict returns. No claim of portfolio profit or a trained impact model is supported.
