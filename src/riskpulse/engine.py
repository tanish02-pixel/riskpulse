import json
import math
import re
import threading
import time
from . import config
from .util import clean_text, phrase_match

UNIVERSE = json.loads((config.ROOT / "data" / "universe.json").read_text())

EVENT_RULES = {
    "Credit Event": (7, ["default", "bankruptcy", "insolvency", "credit downgrade", "debt restructuring", "loan repayment", "liquidity crisis", "missed repayment"]),
    "Geopolitical": (6, ["war", "sanctions", "conflict", "invasion", "tariff", "tariffs", "trade restrictions", "export ban", "export restrictions"]),
    "Macroeconomic": (5, ["inflation", "interest rate", "interest rates", "rate hike", "rate cut", "recession", "federal reserve", "unemployment", "monetary policy"]),
    "Merger/Acquisition": (5, ["acquisition", "acquire", "acquires", "merger", "takeover", "buyout"]),
    "Product Launch": (3, ["launch", "launches", "unveils", "introduces", "new product", "new chip", "new iphone"]),
    "Regulatory": (6, ["antitrust", "regulator", "regulatory", "investigation", "lawsuit", "fine", "fraud", "settlement"]),
    "Operational": (5, ["outage", "recall", "data breach", "cyberattack", "shutdown", "supply chain", "strike", "factory fire"]),
    "Earnings": (4, ["earnings", "revenue", "profit", "profits", "quarterly", "guidance", "sales", "dividend"]),
}

POSITIVE = {
    "beats expectations": 2.4, "record profit": 2.4, "record revenue": 2.3,
    "profit growth": 2.1, "raises guidance": 2.1, "strong demand": 1.8,
    "growth": 1.2, "grows": 1.2, "gain": 1.1, "gains": 1.1,
    "surge": 1.5, "surges": 1.5, "improved": 1.1, "improves": 1.1,
    "approved": 1.1, "successful": 1.2, "outperform": 1.4,
    "expands": 1.1, "expansion": 1.0, "innovation": .7, "launches": .6,
    "unveils": .5, "partnership": 1.0, "recovery": 1.0,
}
NEGATIVE = {
    "misses expectations": 2.4, "cuts guidance": 2.3, "record loss": 2.5,
    "defaults": 3.0, "default": 3.0, "bankruptcy": 3.0,
    "missed repayment": 2.8, "liquidity crisis": 2.8,
    "credit downgrade": 2.2, "decline": 1.5, "declines": 1.5,
    "loss": 1.7, "losses": 1.7, "fraud": 2.5, "outage": 1.8,
    "recall": 1.8, "cyberattack": 2.3, "data breach": 2.3,
    "sanctions": 2.0, "export ban": 2.0, "export restrictions": 1.7,
    "recession": 1.8, "war": 2.4, "lawsuit": 1.5, "fine": 1.2,
    "shutdown": 1.8, "weak demand": 1.8, "slump": 1.9,
}


def fallback_sentiment(text):
    matches, total = [], 0.0
    used = set()
    for polarity, vocabulary in [(1, POSITIVE), (-1, NEGATIVE)]:
        for phrase, magnitude in sorted(vocabulary.items(), key=lambda x: -len(x[0])):
            for match in re.finditer(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, re.I):
                span = set(range(match.start(), match.end()))
                if span & used:
                    continue
                used |= span
                prefix = text[max(0, match.start() - 35):match.start()].lower().split()[-3:]
                negated = any(w in ["not", "no", "never", "without"] for w in prefix)
                signed = polarity * magnitude * (-.8 if negated else 1)
                total += signed
                matches.append({"term": phrase, "direction": "positive" if signed > 0 else "negative"})
    score = math.tanh(total / 3.0)
    confidence = min(.88, .52 + .09 * len(matches)) if matches else .35
    return {"score": round(score, 4), "confidence": round(confidence, 4), "evidence": matches,
            "backend": "financial_lexicon", "label": "neutral" if abs(score) < .12 else "positive" if score > 0 else "negative"}


def classify_event(text):
    candidates = []
    for category, (severity, terms) in EVENT_RULES.items():
        hits = [term for term in terms if phrase_match(text, term)]
        if hits:
            candidates.append((len(hits), severity, category, hits))
    if not candidates:
        return "Other", 2, [], .30
    _, severity, category, hits = max(candidates)
    return category, severity, hits, min(.92, .60 + .08 * len(hits))


def estimate_impact(text, baseline, sentiment, confidence):
    cues = [term for term in ["systemic", "global", "nationwide", "major", "billion", "bankruptcy", "war", "default"] if phrase_match(text, term)]
    mitigation = [term for term in ["rumor", "rumour", "unconfirmed", "denies", "denied", "resolved", "minor"] if phrase_match(text, term)]
    raw = baseline + min(2, len(cues)) + (1 if abs(sentiment) > .65 else 0) - min(3, len(mitigation))
    return max(1, min(10, raw)), {"event_baseline": baseline, "severity_cues": cues,
        "mitigating_cues": mitigation, "sentiment_adjustment": 1 if abs(sentiment) > .65 else 0,
        "method": "Explainable heuristic. Uncalibrated to realized market returns."}


class RiskEngine:
    def __init__(self, backend=None):
        self.requested = backend or config.BACKEND
        self.backend = "financial_lexicon"
        self.model = self.tokenizer = None
        self.model_error = None
        self.loading = False
        self.lock = threading.Lock()

    def load_model(self):
        if self.requested != "finbert" or self.model is not None or self.loading:
            return
        self.loading = True
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            torch.set_num_threads(2)
            local_model = config.ROOT / "runtime" / "models" / "finbert"
            location = str(local_model) if (local_model / "pytorch_model.bin").exists() else config.MODEL_ID
            options = {"local_files_only": True} if location != config.MODEL_ID else {"revision": config.MODEL_REVISION}
            self.tokenizer = AutoTokenizer.from_pretrained(location, **options)
            self.model = AutoModelForSequenceClassification.from_pretrained(location, **options)
            self.model.eval()
            self.backend = "finbert"
            self.model_error = None
        except Exception as exc:
            self.model_error = str(exc)[:280]
        finally:
            self.loading = False

    def sentiment(self, text):
        if self.model is None:
            return fallback_sentiment(text)
        import torch
        with self.lock, torch.inference_mode():
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
            probs = torch.softmax(self.model(**inputs).logits, dim=-1)[0].tolist()
        labels = {str(self.model.config.id2label[i]).lower(): probs[i] for i in range(len(probs))}
        score = labels.get("positive", 0) - labels.get("negative", 0)
        return {"score": round(score, 4), "confidence": round(max(probs), 4),
            "backend": "finbert", "label": max(labels, key=labels.get), "probabilities": labels,
            "evidence": []}

    def analyze(self, title, body="", tickers=None):
        started = time.perf_counter()
        text = clean_text(title + " " + body)[:12000]
        matches = [stock["ticker"] for stock in UNIVERSE if any(phrase_match(text, a) for a in stock["aliases"])]
        entities = list(dict.fromkeys(tickers or matches))
        signals = []
        for ticker in entities or [None]:
            focused = text
            entity_scope = "global_event" if ticker is None else "single_company"
            if len(matches) > 1 and ticker:
                aliases = next(s["aliases"] for s in UNIVERSE if s["ticker"] == ticker)
                sentences = re.split(r"(?<=[.!?;])\s+", text)
                focus = [sentence for sentence in sentences if any(phrase_match(sentence, a) for a in aliases)]
                focused = " ".join(focus) or text
                entity_scope = "sentence_context" if len(focus) < len(sentences) else "shared_context"
            sentiment = self.sentiment(focused)
            event, baseline, terms, event_confidence = classify_event(focused)
            impact, breakdown = estimate_impact(focused, baseline, sentiment["score"], sentiment["confidence"])
            signals.append({"ticker": ticker, "sentiment_score": sentiment["score"],
                "sentiment_label": sentiment["label"], "confidence": sentiment["confidence"],
                "event_classification": event, "event_confidence": event_confidence,
                "impact_score": impact, "impact_method": "heuristic",
                "event_evidence": terms, "sentiment_evidence": sentiment.get("evidence", []),
                "probabilities": sentiment.get("probabilities"), "impact_breakdown": breakdown,
                "model_backend": sentiment["backend"], "entity_scope": entity_scope,
                "analysis_text": focused[:1500], "latency_ms": round((time.perf_counter() - started) * 1000, 2)})
        return signals

    def status(self):
        return {"requested": self.requested, "active": self.backend, "loading": self.loading,
            "model_id": config.MODEL_ID if self.model is not None else None,
            "model_error": self.model_error, "event_method": "Auditable phrase classifier",
            "impact_method": "Uncalibrated severity heuristic"}

