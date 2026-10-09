import hashlib
import html
import re
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def parse_time(value):
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def clean_text(text):
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def fingerprint(text):
    normalized = re.sub(r"[^a-z0-9]+", " ", clean_text(text).lower()).strip()
    return hashlib.sha256(normalized.encode()).hexdigest()


def phrase_match(text, phrase):
    return re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, re.I) is not None

