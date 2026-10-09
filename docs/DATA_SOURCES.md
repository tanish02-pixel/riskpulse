# Data sources and attribution

## Live text

- BBC Business RSS: https://feeds.bbci.co.uk/news/business/rss.xml
- Apple Newsroom: https://www.apple.com/newsroom/rss-feed.rss
- Microsoft corporate blog: https://blogs.microsoft.com/feed/
- Yahoo Finance optional headlines: https://finance.yahoo.com/rss/headline?s=AAPL,MSFT,NVDA,AMZN,GOOGL,META,JPM,XOM,JNJ,WMT
- GDELT DOC API optional: https://api.gdeltproject.org/api/v2/doc/doc
- GDELT API explanation: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/

The connectors consume provider-returned headlines and summaries. No API credential is included. Provider availability, terms and rate limits still apply. Article copyright remains with providers. The submitted datasets contain synthetic text, not redistributed live article collections. The runtime database is excluded from the repository. The source-type reliability numbers are design coefficients, not empirical reliability measurements.

RSS publication/update times drive age filtering. The engine flags missing timestamps as inferred. GDELT `seendate` is observation/discovery time, rather than verified publication time.

## Pretrained model

- Model: https://huggingface.co/ProsusAI/finbert
- Source implementation and model license: https://github.com/ProsusAI/finBERT
- Pinned model revision: `4556d13015211d73dccd3fdd39d39232506f3e43`
- FinBERT paper: https://arxiv.org/abs/1908.10063

FinBERT is a pretrained model credited to its authors. The upstream repository identifies the model under Apache-2.0. RiskPulse does not fine-tune it or redistribute its weights in the source ZIP. Setup downloads official files and records hashes. Check upstream licenses when distributing a deployment with bundled weights.

## Synthetic fixtures

`replay_events.json` contains 12 fictional events authored for demonstration. `evaluation.json` contains 24 separately authored synthetic sanity cases, balanced across positive, negative and neutral sentiment. `sample_import.csv` mirrors the replay texts. All fictional event headlines carry a Synthetic label in the replay dataset. These fixtures use the project's MIT license. They contain no personal, confidential or client transaction data. There is no supplied wholesale-banking transaction dataset in this project, because Module A is the selected downstream module.

## Photograph and libraries

Presentation photograph: Andrea De Santis, Unsplash.
Source page: https://unsplash.com/photos/a-group-of-buildings-that-are-next-to-each-other-cV8BIJolid4
Unsplash license: https://unsplash.com/license
The photo is decorative architecture imagery, not a screenshot or evidence of an actual market event.

Frameworks include FastAPI, Uvicorn, Pydantic, HTTPX, feedparser, PyTorch, Transformers, React, Vite, Recharts and Lucide. They retain their upstream licenses. Backend dependency files and the frontend lockfile identify installed versions. The project MIT license covers original project code, not those dependencies.
