import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_env():
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_env()
DB_PATH = Path(os.getenv("RISKPULSE_DB", str(ROOT / "runtime" / "riskpulse.db")))
BACKEND = os.getenv("SENTIMENT_BACKEND", "finbert")
POLL_SECONDS = max(120, int(os.getenv("POLL_SECONDS", "300")))
API_TOKEN = os.getenv("RISKPULSE_API_TOKEN", "")
AUTO_POLL = os.getenv("AUTO_POLL", "false").lower() == "true"
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
MODEL_ID = "ProsusAI/finbert"
MODEL_REVISION = "4556d13015211d73dccd3fdd39d39232506f3e43"

