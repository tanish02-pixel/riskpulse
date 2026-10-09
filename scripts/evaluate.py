import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from riskpulse.engine import RiskEngine


def evaluate():
    engine = RiskEngine("finbert")
    engine.load_model()
    cases = json.loads((ROOT / "data" / "evaluation.json").read_text())
    results, latency = [], []
    labels = ["positive", "negative", "neutral"]
    confusion = {gold: {pred: 0 for pred in labels} for gold in labels}
    for case in cases:
        start = time.perf_counter()
        predicted = engine.analyze(case["text"])[0]
        elapsed = (time.perf_counter() - start) * 1000
        latency.append(elapsed)
        confusion[case["sentiment"]][predicted["sentiment_label"]] += 1
        results.append({**case, "predicted_sentiment": predicted["sentiment_label"],
            "predicted_event": predicted["event_classification"], "sentiment_score": predicted["sentiment_score"],
            "impact_score": predicted["impact_score"], "latency_ms": round(elapsed, 2)})
    count = len(cases)
    report = {"scope": "24 independently authored synthetic sanity cases. No training or tuning on these cases. This is not a real-news benchmark or a return-prediction evaluation.",
        "backend": engine.backend, "cases": count,
        "sentiment_correct": sum(r["sentiment"] == r["predicted_sentiment"] for r in results),
        "event_correct": sum(r["event"] == r["predicted_event"] for r in results),
        "mean_latency_ms": round(sum(latency) / count, 2),
        "p95_latency_ms": round(sorted(latency)[int(.95 * (count - 1))], 2),
        "confusion_matrix": confusion, "results": results,
        "impact_note": "Impact scores are deterministic severity estimates. No empirical calibration or impact-accuracy claim."}
    (ROOT / "docs" / "evaluation_results.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k not in ["results", "confusion_matrix"]}, indent=2))


if __name__ == "__main__":
    evaluate()

