import json
import threading
from datetime import datetime, timedelta, timezone
from . import config
from .engine import RiskEngine, UNIVERSE
from .feeds import SOURCES, fetch_source
from .portfolio import DEFAULT_POLICY, rebalance
from .storage import Store
from .util import fingerprint, now_iso


class RiskService:
    def __init__(self, path=None, backend=None):
        self.store = Store(path or config.DB_PATH)
        self.engine = RiskEngine(backend)
        self.lock = threading.RLock()
        self.live_lock = threading.Lock()
        self.polling = config.AUTO_POLL
        self.tickers = [stock["ticker"] for stock in UNIVERSE]
        for mode in ["live", "replay"]:
            if not self.store.history(mode, 1):
                equal = {ticker: 1 / len(self.tickers) for ticker in self.tickers}
                self.store.snapshot(mode, "Initial equal allocation", {"before": equal, "after": equal, "turnover": 0, "scores": {}, "ignored": {}, "policy": DEFAULT_POLICY})

    def policy(self):
        return self.store.settings("policy", DEFAULT_POLICY)

    def ingest(self, article, auto_rebalance=True):
        with self.lock:
            content_hash = fingerprint(article["title"])
            if self.store.has_fingerprint(content_hash):
                return {"duplicate": True, "signals": []}
            signals = self.engine.analyze(article["title"], article.get("body", ""), article.get("tickers"))
            for signal in signals:
                signal["source_reliability"] = article.get("source_reliability", .8)
                signal["timestamp_inferred"] = article.get("timestamp_inferred", False)
            result = self.store.add_article(article, signals, content_hash)
            if result is None:
                return {"duplicate": True, "signals": []}
            enriched = [{**signal, "id": sid, "published_at": article["published_at"]} for signal, sid in zip(signals, result["signal_ids"])]
            snapshot = self.rebalance(article["mode"], "New text: " + article["title"][:100]) if auto_rebalance else None
            return {**result, "duplicate": False, "signals": enriched, "rebalance": snapshot}

    def rebalance(self, mode, reason="Manual recomputation"):
        with self.lock:
            result = rebalance(self.tickers, self.store.current(mode, self.tickers), self.store.signals(mode, limit=5000), self.policy())
            if result["changed"]:
                result["snapshot_id"] = self.store.snapshot(mode, reason, result)
            return result

    def refresh_live(self, source_ids=None):
        if not self.live_lock.acquire(blocking=False):
            return {"busy": True, "message": "A refresh is already running"}
        try:
            selected = [source for source in SOURCES if not source_ids or source["id"] in source_ids]
            results = []
            for source in selected:
                previous = self.store.sources().get(source["id"], {})
                try:
                    if previous.get("last_checked"):
                        from .util import parse_time
                        if (datetime.now(timezone.utc) - parse_time(previous["last_checked"])).total_seconds() < 30:
                            results.append({"source": source["id"], "skipped": "30-second cooldown"})
                            continue
                    articles, status = fetch_source(source)
                    added, duplicates = 0, 0
                    for article in reversed(articles):
                        r = self.ingest(article, auto_rebalance=False)
                        duplicates += int(r["duplicate"])
                        added += int(not r["duplicate"])
                    status.update({"added": added, "duplicates": duplicates})
                    self.store.set_source(source["id"], status)
                    results.append({"source": source["id"], **status})
                except Exception as exc:
                    status = {**previous, "status": "error", "last_checked": now_iso(), "error": str(exc)[:300]}
                    self.store.set_source(source["id"], status)
                    results.append({"source": source["id"], **status})
            self.rebalance("live", "Live source batch")
            return {"busy": False, "sources": results}
        finally:
            self.live_lock.release()

    def replay(self, reset=False, count=None):
        with self.lock:
            if reset:
                self.store.reset_replay()
                equal = {ticker: 1 / len(self.tickers) for ticker in self.tickers}
                self.store.snapshot("replay", "Replay reset", {"before": equal, "after": equal, "turnover": 0, "scores": {}, "ignored": {}, "policy": self.policy()})
            events = json.loads((config.ROOT / "data" / "replay_events.json").read_text())
            ingested = 0
            for i, event in enumerate(events):
                if self.store.has_fingerprint(fingerprint(event["title"])):
                    continue
                article = {**event, "mode": "replay", "published_at": (datetime.now(timezone.utc) - timedelta(minutes=len(events) - i)).isoformat(),
                    "source_reliability": .80, "url": "", "source": "Synthetic " + event["source_type"].replace("_", " ")}
                self.ingest(article)
                ingested += 1
                if count and ingested >= count:
                    break
            return {"ingested": ingested, "remaining": sum(not self.store.has_fingerprint(fingerprint(event["title"])) for event in events), "mode": "replay"}

    def overview(self, mode):
        signals = self.store.signals(mode, limit=5000)
        current = self.store.current(mode, self.tickers)
        history = self.store.history(mode, 120)
        last = history[-1] if history else {}
        distribution = {label: sum(s["sentiment_label"] == label for s in signals) for label in ["positive", "neutral", "negative"]}
        return {"mode": mode, "universe": UNIVERSE, "weights": current, "history": history,
            "counts": self.store.counts(mode), "distribution": distribution,
            "high_impact": sum(s["impact_score"] >= 8 for s in signals),
            "mean_sentiment": round(sum(s["sentiment_score"] for s in signals) / len(signals), 4) if signals else 0,
            "last_rebalance": last, "policy": self.policy(), "model": self.engine.status(),
            "polling": self.polling, "poll_seconds": config.POLL_SECONDS,
            "sources": [{**source, **self.store.sources().get(source["id"], {"status": "idle"})} for source in SOURCES],
            "allocation_total": sum(current.values()), "server_time": now_iso()}

