import json
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import feedparser
import httpx
from .util import clean_text, now_iso

SOURCES = [
    {"id": "bbc_business", "name": "BBC Business", "type": "financial_news", "kind": "rss",
     "url": "https://feeds.bbci.co.uk/news/business/rss.xml", "reliability": .85},
    {"id": "yahoo_news", "name": "Yahoo Finance headlines", "type": "financial_news", "kind": "rss",
     "url": "https://finance.yahoo.com/rss/headline?s=AAPL,MSFT,NVDA,AMZN,GOOGL,META,JPM,XOM,JNJ,WMT", "reliability": .85},
    {"id": "apple_newsroom", "name": "Apple Newsroom", "type": "company_announcement", "kind": "rss",
     "url": "https://www.apple.com/newsroom/rss-feed.rss", "reliability": .92},
    {"id": "microsoft_blog", "name": "Microsoft corporate blog", "type": "company_announcement", "kind": "rss",
     "url": "https://blogs.microsoft.com/feed/", "reliability": .90},
    {"id": "gdelt", "name": "GDELT global news", "type": "financial_news", "kind": "gdelt", "reliability": .80,
     "url": "https://api.gdeltproject.org/api/v2/doc/doc"},
]


def parse_feed(raw, source):
    feed = feedparser.parse(raw)
    if not getattr(feed, "version", ""):
        raise ValueError("Feed response was not valid RSS/Atom")
    result = []
    for entry in feed.entries[:20]:
        title = clean_text(entry.get("title", ""))
        if not title:
            continue
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        published = datetime(*parsed[:6], tzinfo=timezone.utc).isoformat() if parsed else now_iso()
        result.append({"title": title[:1000], "body": clean_text(entry.get("summary", ""))[:10000],
            "source": source["name"], "source_type": source["type"], "url": entry.get("link", ""),
            "published_at": published, "mode": "live", "source_reliability": source["reliability"],
            "timestamp_inferred": parsed is None})
    return result


def parse_gdelt(raw, source):
    payload = json.loads(raw)
    result = []
    for entry in payload.get("articles", [])[:20]:
        date = entry.get("seendate", "")
        try:
            published = datetime.strptime(date, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            published = now_iso()
        result.append({"title": clean_text(entry["title"])[:1000], "body": "",
            "source": "GDELT: " + entry.get("domain", "unknown"), "source_type": source["type"],
            "url": entry.get("url", ""), "published_at": published, "mode": "live",
            "source_reliability": source["reliability"], "timestamp_inferred": not bool(date)})
    return result


def fetch_source(source):
    params = None
    if source["kind"] == "gdelt":
        params = {"query": '("Apple" OR "Microsoft" OR "Nvidia" OR "JPMorgan" OR "Exxon") sourcelang:english',
            "mode": "artlist", "format": "json", "maxrecords": 20, "timespan": "1day", "sort": "datedesc"}
    started = time.perf_counter()
    with httpx.Client(timeout=18, follow_redirects=True, headers={"User-Agent": "RiskPulseAcademic/1.0 (research prototype)", "Accept": "application/rss+xml,application/atom+xml,application/json,text/xml"}) as client:
        with client.stream("GET", source["url"], params=params) as response:
            response.raise_for_status()
            chunks, size = [], 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > 2_000_000:
                    raise ValueError("Feed response exceeded 2 MB")
                chunks.append(chunk)
    raw = b"".join(chunks)
    articles = parse_gdelt(raw, source) if source["kind"] == "gdelt" else parse_feed(raw, source)
    return articles, {"status": "ok", "last_checked": now_iso(), "last_success": now_iso(),
        "items_returned": len(articles), "latency_ms": round((time.perf_counter() - started) * 1000), "error": None}

