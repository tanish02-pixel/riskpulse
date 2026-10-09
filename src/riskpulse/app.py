import asyncio
import csv
import io
import json
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal
from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Header, Depends
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator
from . import config
from .engine import UNIVERSE
from .portfolio import bounded_simplex
from .service import RiskService
from .util import now_iso, clean_text

service = RiskService()
Mode = Literal["live", "replay"]
Ticker = Literal["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "JPM", "XOM", "JNJ", "WMT"]


class ArticleInput(BaseModel):
    title: str = Field(min_length=5, max_length=1000)
    body: str = Field(default="", max_length=12000)
    source: str = Field(default="Analyst input", max_length=120)
    source_type: Literal["financial_news", "company_announcement", "social_media", "analyst_input"] = "analyst_input"
    published_at: datetime | None = None
    mode: Mode = "replay"
    tickers: list[Ticker] | None = None
    url: str = Field(default="", max_length=1500)

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, value):
        if len(clean_text(value)) < 5:
            raise ValueError("Provide at least five characters of text")
        return clean_text(value)

    @field_validator("published_at")
    @classmethod
    def check_time(cls, value):
        if value is not None:
            value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
            if (value - datetime.now(timezone.utc)).total_seconds() > 3600:
                raise ValueError("Publication time must not be more than one hour in the future")
        return value

    @field_validator("url")
    @classmethod
    def check_url(cls, value):
        if value and not value.startswith(("https://", "http://")):
            raise ValueError("Source URL must use HTTP or HTTPS")
        return value

    def article(self):
        value = self.model_dump()
        value["published_at"] = self.published_at.isoformat() if self.published_at else now_iso()
        value["source_reliability"] = .7
        return value


class ReplayInput(BaseModel):
    reset: bool = False
    count: int | None = Field(default=None, ge=1, le=50)


class PollInput(BaseModel):
    enabled: bool


class RefreshInput(BaseModel):
    source_ids: list[Literal["bbc_business", "yahoo_news", "apple_newsroom", "microsoft_blog", "gdelt"]] | None = None


class PolicyInput(BaseModel):
    sensitivity: float = Field(default=.35, ge=.01, le=1)
    min_weight: float = Field(default=.02, ge=0, le=.09)
    max_weight: float = Field(default=.18, ge=.10, le=.50)
    max_turnover: float = Field(default=.10, ge=.001, le=.50)
    half_life_hours: float = Field(default=12, ge=.5, le=168)
    min_confidence: float = Field(default=.55, ge=0, le=1)
    min_sentiment: float = Field(default=.08, ge=0, le=1)
    max_age_hours: float = Field(default=72, ge=1, le=720)

    @model_validator(mode="after")
    def bounds(self):
        if self.min_weight > self.max_weight:
            raise ValueError("Minimum weight must be below maximum weight")
        return self


def authorized(x_riskpulse_token: str = Header(default="")):
    if config.API_TOKEN and not secrets.compare_digest(x_riskpulse_token, config.API_TOKEN):
        raise HTTPException(401, "Set your API token in the dashboard connection settings")


async def poll_loop():
    while True:
        if service.polling:
            await asyncio.to_thread(service.refresh_live)
        await asyncio.sleep(config.POLL_SECONDS)


@asynccontextmanager
async def lifespan(app):
    model_task = asyncio.create_task(asyncio.to_thread(service.engine.load_model))
    poll_task = asyncio.create_task(poll_loop())
    yield
    poll_task.cancel()
    await asyncio.gather(poll_task, return_exceptions=True)
    if not model_task.done():
        model_task.cancel()


app = FastAPI(title="RiskPulse API", version="1.0.0", lifespan=lifespan,
    description="Financial text signals and constrained mock index allocation. Live and synthetic replay records remain separate.")


@app.middleware("http")
async def response_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api") else "no-cache"
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'"
    if request.url.path in {"/docs", "/redoc"}:
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data: https://fastapi.tiangolo.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; connect-src 'self'; object-src 'none'; frame-ancestors 'none'"
    return response


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0", "model": service.engine.status(), "time": now_iso()}


@app.get("/api/overview", dependencies=[Depends(authorized)])
def overview(mode: Mode = "live"):
    return service.overview(mode)


@app.get("/api/signals", dependencies=[Depends(authorized)])
def signals(mode: Mode = "live", ticker: Ticker | None = None, event: str | None = None,
            search: str | None = Query(default=None, max_length=200), limit: int = Query(default=200, ge=1, le=5000)):
    return {"items": service.store.signals(mode, ticker, event, search, limit)}


@app.post("/api/ingest", dependencies=[Depends(authorized)])
def ingest(article: ArticleInput):
    return service.ingest(article.article())


@app.post("/api/analyze", dependencies=[Depends(authorized)])
def analyze(article: ArticleInput):
    return {"signals": service.engine.analyze(article.title, article.body, article.tickers), "saved": False}


@app.post("/api/replay", dependencies=[Depends(authorized)])
def replay(request: ReplayInput):
    return service.replay(request.reset, request.count)


@app.post("/api/refresh", dependencies=[Depends(authorized)])
def refresh(request: RefreshInput):
    return service.refresh_live(request.source_ids)


@app.post("/api/rebalance", dependencies=[Depends(authorized)])
def recompute(mode: Mode = "live"):
    return service.rebalance(mode)


@app.post("/api/polling", dependencies=[Depends(authorized)])
def polling(request: PollInput):
    service.polling = request.enabled
    return {"enabled": service.polling, "interval_seconds": config.POLL_SECONDS}


@app.put("/api/policy", dependencies=[Depends(authorized)])
def policy(request: PolicyInput):
    with service.lock:
        settings = request.model_dump()
        service.store.set_settings("policy", settings)
        for mode in ["live", "replay"]:
            before = service.store.current(mode, service.tickers)
            compliant = bounded_simplex(list(before.values()), settings["min_weight"], settings["max_weight"])
            if any(abs(before[ticker] - value) > 1e-8 for ticker, value in zip(service.tickers, compliant)):
                after = dict(zip(service.tickers, compliant))
                service.store.snapshot(mode, "Compliance with updated weight limits", {"before": before, "after": after,
                    "turnover": .5 * sum(abs(before[t] - after[t]) for t in before), "scores": {}, "ignored": {}, "policy": settings})
            service.rebalance(mode, "Policy update")
    return settings


@app.post("/api/import", dependencies=[Depends(authorized)])
async def import_file(file: UploadFile = File(...), mode: Mode = "replay"):
    raw = await file.read(256_001)
    if len(raw) > 256_000:
        raise HTTPException(413, "Import limit is 256 KB and 100 records")
    try:
        text = raw.decode("utf-8-sig")
        if (file.filename or "").lower().endswith(".json"):
            rows = json.loads(text)
        elif (file.filename or "").lower().endswith(".csv"):
            rows = list(csv.DictReader(io.StringIO(text)))
        else:
            raise ValueError("Use a CSV or JSON file")
        if not isinstance(rows, list) or len(rows) > 100:
            raise ValueError("Provide an array of at most 100 records")
        validated = []
        for row in rows:
            row = dict(row)
            row["mode"] = mode
            if isinstance(row.get("tickers"), str):
                row["tickers"] = [ticker.strip() for ticker in row["tickers"].split(",") if ticker.strip()] or None
            if not row.get("published_at"):
                row.pop("published_at", None)
            validated.append(ArticleInput.model_validate(row))
    except Exception as exc:
        raise HTTPException(422, "Import validation failed: " + str(exc)[:400]) from exc
    results = [await asyncio.to_thread(service.ingest, row.article()) for row in validated]
    return {"ingested": sum(not result["duplicate"] for result in results), "duplicates": sum(result["duplicate"] for result in results)}


@app.get("/api/export", dependencies=[Depends(authorized)])
def export(mode: Mode = "live", format: Literal["json", "csv"] = "json"):
    items = service.store.signals(mode, limit=5000)
    if format == "json":
        return Response(json.dumps(items, indent=2), media_type="application/json", headers={"Content-Disposition": 'attachment; filename="riskpulse_signals_' + mode + '.json"'})
    output = io.StringIO()
    fields = ["id", "ticker", "title", "source", "source_type", "published_at", "sentiment_score", "sentiment_label", "confidence", "event_classification", "impact_score", "model_backend", "mode"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for item in items:
        safe = {k: ("'" + value if isinstance(value, str) and value.startswith(("=", "+", "-", "@")) else value) for k, value in item.items()}
        writer.writerow(safe)
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="riskpulse_signals_' + mode + '.csv"'})


DIST = config.ROOT / "frontend" / "dist"
if (DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")


@app.get("/favicon.svg")
def favicon():
    return FileResponse(config.ROOT / "frontend" / "public" / "favicon.svg")


@app.get("/")
def homepage():
    if not (DIST / "index.html").exists():
        raise HTTPException(503, "Frontend build missing. Run npm ci and npm run build in frontend/")
    return FileResponse(DIST / "index.html")

