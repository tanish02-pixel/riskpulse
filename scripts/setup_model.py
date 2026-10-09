"""Download the official FinBERT files once; subsequent inference stays local."""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from riskpulse import config


def main():
    destination = ROOT / "runtime" / "models" / "finbert"
    destination.mkdir(parents=True, exist_ok=True)
    files = ["config.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt", "pytorch_model.bin"]
    manifest = {"model": config.MODEL_ID, "revision": config.MODEL_REVISION, "files": {}}
    for name in files:
        target = destination / name
        if not target.exists():
            print("Downloading", name, flush=True)
            url = "https://huggingface.co/" + config.MODEL_ID + "/resolve/" + config.MODEL_REVISION + "/" + name
            temp = target.with_suffix(target.suffix + ".part")
            try:
                with urllib.request.urlopen(url, timeout=90) as response, temp.open("wb") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
                if temp.stat().st_size < 10:
                    raise ValueError("Empty model artifact")
                temp.replace(target)
            except Exception:
                temp.unlink(missing_ok=True)
                raise
        digest = hashlib.sha256()
        with target.open("rb") as file:
            while chunk := file.read(1024 * 1024):
                digest.update(chunk)
        manifest["files"][name] = {"sha256": digest.hexdigest(), "bytes": target.stat().st_size}
    (destination / "download_manifest.json").write_text(json.dumps(manifest, indent=2))
    from riskpulse.engine import RiskEngine
    engine = RiskEngine("finbert")
    engine.load_model()
    if engine.model is None:
        raise RuntimeError("Files downloaded but model loading failed: " + str(engine.model_error))
    print("FinBERT ready. CPU inference check:", engine.sentiment("The company reports strong growth and record profit."))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("FinBERT setup failed:", exc, file=sys.stderr)
        print("Install requirements-ml.txt and retry. The server exposes fallback status if unavailable.", file=sys.stderr)
        sys.exit(1)

