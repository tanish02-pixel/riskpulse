# Architecture and design decisions

## Component mapping

| Component | File | Responsibility |
|---|---|---|
| Fixed connectors | `src/riskpulse/feeds.py` | Bounded HTTP fetches, RSS/Atom/GDELT parsing, source/time provenance |
| NLP engine | `src/riskpulse/engine.py` | Entity aliases, FinBERT/lexicon sentiment, event rules, severity evidence |
| Allocation | `src/riskpulse/portfolio.py` | Signal eligibility, decay, aggregation, bounded targets, turnover |
| Persistent store | `src/riskpulse/storage.py` | SQLite articles, signals, policy, source status and history |
| Orchestration | `src/riskpulse/service.py` | Ingestion, deduplication, refresh batches, replay, rebalance |
| API | `src/riskpulse/app.py` | Validated requests, optional token, export/import, static dashboard |
| Dashboard | `frontend/src/main.jsx` | Live/replay views, signals, source status, charts and policy controls |

A single FastAPI process owns a persistent SQLite store. A background thread loads the sentiment model. A polling task calls blocking connectors through `asyncio.to_thread`. CPU inference uses two PyTorch threads and a model lock. Ingestion/rebalancing uses an application lock to keep signal writes and allocation updates coherent. SQLite uses WAL and closed connections per operation. This prototype has no distributed queue or multi-worker deployment contract.

## Ingestion and provenance

The fixed connector list limits arbitrary server URL fetching. Each response has an 18-second timeout and a 2 MB size limit. Feed HTML is stripped. Normalized headline fingerprints suppress repeated headlines across sources and modes. This conservative deduplication can suppress a distinct story sharing a normalized title, and changed titles can remain separate. A production system needs richer content/event clustering.

RSS keeps publication/update timestamps. If missing, ingestion time is marked as inferred. GDELT discovery time differs from publication time. No full-article scraper is implemented. Manual imports validate every row before writing, with a 100-row/256 KB limit. Database/inference failures during the later write phase are not a guaranteed all-or-nothing batch transaction.

## Model behavior

The pinned FinBERT revision is `4556d13015211d73dccd3fdd39d39232506f3e43`. Setup downloads official model files once. Inference truncates to 256 tokens. The score is positive probability minus negative probability. Confidence is the maximum class probability, not calibrated market-outcome confidence. If dependencies/model loading fail, a negation-aware financial lexicon keeps the application usable. Every signal records which backend actually analyzed it. Previously saved fallback signals are not automatically rescored after FinBERT becomes ready. Load FinBERT before the demonstration, then reset replay to rerun its fixtures.

Entity resolution uses company aliases, not a trained NER/linking system. Multi-company articles use sentence-level context where possible. Shared/ambiguous context remains visible but cannot tilt individual stock weights. Manual company mapping can override automatic mapping, so a reviewer should verify the selected ticker.

Event classification returns one dominant phrase category and matched terms. A phrase match alone cannot distinguish all negated, rumored or hypothetical events. The severity score is an explainable event-baseline/cue heuristic. It has no ground-truth realized-impact calibration. These are explicit limits of the hackathon scope.

## Index policy

The target always starts from the equal-weight baseline, rather than multiplying current weights repeatedly. Eligible signals contribute confidence, assumed source reliability and exponential time decay. A weighted mean attenuated by available strength controls the tilt. Exponential targets normalize to 100%. A bounded-simplex projection enforces stock floor/cap. Interpolation enforces normal per-update one-way turnover. Recomputing the same text can finish movement toward an unchanged target after a turnover-limited step, but does not increase that target itself.

A policy update first brings current weights into new mandatory bounds, recording a compliance snapshot. This correction can exceed normal turnover. Subsequent sentiment updates follow the new turnover setting. Policy applies to both portfolios, while their underlying text/snapshots remain separate.

Global events remain searchable risk intelligence. Module A does not invent company-level exposure for them. Module B is a future extension and is not implemented. An event-impact API is available for a later stress-testing consumer.

## Reliability and deployment scope

Source failures persist in status with last check/success and error. Replay never silently replaces a live feed. Mode filtering applies to signals, allocation and export. Headlines, signals and changed allocations persist over restarts. The background polling toggle lasts for the running server; `AUTO_POLL` controls restart behavior.

The default server binds to localhost. Optional token authentication protects data and mutation endpoints. Import limits, URL checks, response headers and CSV formula escaping cover common prototype hazards. This does not provide a complete production security, compliance or resilience framework. A production plan would add HTTPS, user roles, rate limiting, operational monitoring and licensed feeds before trading integration.
