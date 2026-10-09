import math
from datetime import datetime, timezone
from .util import parse_time

DEFAULT_POLICY = {"sensitivity": .35, "min_weight": .02, "max_weight": .18,
                  "max_turnover": .10, "half_life_hours": 12, "min_confidence": .55,
                  "min_sentiment": .08, "max_age_hours": 72}


def bounded_simplex(raw, floor, cap):
    n = len(raw)
    if not n or n * floor > 1 or n * cap < 1:
        raise ValueError("Weight limits cannot allocate 100% across the universe")
    lo, hi = min(raw) - cap, max(raw) - floor
    for _ in range(100):
        mid = (lo + hi) / 2
        candidate = [max(floor, min(cap, value - mid)) for value in raw]
        if sum(candidate) > 1:
            lo = mid
        else:
            hi = mid
    weights = [max(floor, min(cap, value - (lo + hi) / 2)) for value in raw]
    correction = 1 - sum(weights)
    for i, value in enumerate(weights):
        change = max(floor - value, min(cap - value, correction))
        weights[i] += change
        correction -= change
        if abs(correction) < 1e-12:
            break
    return weights


def rebalance(tickers, current, signals, policy=None, now=None):
    policy = {**DEFAULT_POLICY, **(policy or {})}
    now = now or datetime.now(timezone.utc)
    aggregates = {ticker: [] for ticker in tickers}
    ignored = {"global": 0, "stale": 0, "low_confidence": 0, "neutral": 0, "shared_context": 0, "future": 0}
    for signal in signals:
        ticker = signal.get("ticker")
        if ticker not in aggregates:
            ignored["global"] += 1
            continue
        if signal.get("entity_scope") == "shared_context":
            ignored["shared_context"] += 1
            continue
        age = (now - parse_time(signal["published_at"])).total_seconds() / 3600
        if age < -1:
            ignored["future"] += 1
            continue
        if age > policy["max_age_hours"]:
            ignored["stale"] += 1
            continue
        if signal["confidence"] < policy["min_confidence"]:
            ignored["low_confidence"] += 1
            continue
        if signal.get("sentiment_label") == "neutral" or abs(signal["sentiment_score"]) < policy["min_sentiment"]:
            ignored["neutral"] += 1
            continue
        decay = .5 ** (max(0, age) / policy["half_life_hours"])
        strength = signal["confidence"] * signal.get("source_reliability", .8) * decay
        aggregates[ticker].append((signal["sentiment_score"], strength, signal["id"]))
    scores, details = {}, {}
    for ticker, values in aggregates.items():
        strength = sum(value[1] for value in values)
        weighted_mean = sum(v[0] * v[1] for v in values) / strength if strength else 0
        scores[ticker] = weighted_mean * min(1, strength)
        details[ticker] = {"score": round(scores[ticker], 5), "signal_ids": [v[2] for v in values], "count": len(values)}
    base = 1 / len(tickers)
    raw = [base * math.exp(policy["sensitivity"] * scores[ticker]) for ticker in tickers]
    raw = [value / sum(raw) for value in raw]
    target = bounded_simplex(raw, policy["min_weight"], policy["max_weight"])
    before = [current.get(ticker, base) for ticker in tickers]
    turnover = .5 * sum(abs(a - b) for a, b in zip(target, before))
    scale = min(1, policy["max_turnover"] / turnover) if turnover else 1
    after = [a + scale * (b - a) for a, b in zip(before, target)]
    return {"before": dict(zip(tickers, before)), "after": dict(zip(tickers, after)),
        "target": dict(zip(tickers, target)), "turnover": .5 * sum(abs(a - b) for a, b in zip(before, after)),
        "scores": details, "ignored": ignored, "policy": policy,
        "changed": max(abs(a - b) for a, b in zip(before, after)) > 1e-8}

