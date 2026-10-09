import importlib
import pytest
from fastapi.testclient import TestClient
from riskpulse.service import RiskService


@pytest.fixture
def client(tmp_path,monkeypatch):
    appmodule=importlib.import_module("riskpulse.app")
    monkeypatch.setattr(appmodule,"service",RiskService(tmp_path/"api.db","lexicon"))
    monkeypatch.setattr(appmodule.config,"API_TOKEN","")
    with TestClient(appmodule.app) as c:yield c


def test_api_replay_signals_export_and_policy(client):
    assert client.get('/api/health').status_code==200
    assert client.post('/api/replay',json={"reset":True}).json()["ingested"]==12
    signals=client.get('/api/signals?mode=replay').json()["items"]
    assert {"sentiment_score","event_classification","impact_score"}<=signals[0].keys()
    assert all(-1<=s["sentiment_score"]<=1 and 1<=s["impact_score"]<=10 for s in signals)
    csv=client.get('/api/export?mode=replay&format=csv')
    assert csv.status_code==200 and 'sentiment_score' in csv.text
    assert client.put('/api/policy',json={"max_weight":.1}).status_code==200
    overview=client.get('/api/overview?mode=replay').json()
    assert sum(overview["weights"].values())==pytest.approx(1)
    assert all(v<=.1+1e-10 for v in overview["weights"].values())


def test_input_validation_and_import_atomic_validation(client):
    assert client.post('/api/ingest',json={"title":"tiny"}).status_code==422
    assert client.post('/api/ingest',json={"title":"Apple news","tickers":["BAD"]}).status_code==422
    assert client.post('/api/ingest',json={"title":"Apple news","url":"javascript:alert(1)"}).status_code==422
    assert client.post('/api/import',files={"file":("data.json",b'[{"title":"Apple reports growth"},{"title":"x"}]',"application/json")}).status_code==422
    assert client.get('/api/overview?mode=replay').json()["counts"]["articles"]==0


def test_duplicate_no_extra_portfolio_snapshot(client):
    article={"title":"Apple reports record profit and strong growth","mode":"replay"}
    first=client.post('/api/ingest',json=article).json()
    second=client.post('/api/ingest',json=article).json()
    assert not first["duplicate"] and second["duplicate"]
    overview=client.get('/api/overview?mode=replay').json()
    assert overview["counts"]["articles"]==1


def test_authorization_and_error_modes(client,monkeypatch):
    import riskpulse.config as config
    monkeypatch.setattr(config,"API_TOKEN","test-token")
    assert client.get('/api/overview').status_code==401
    assert client.get('/api/overview',headers={"X-RiskPulse-Token":"test-token"}).status_code==200
    assert client.get('/api/overview?mode=unknown',headers={"X-RiskPulse-Token":"test-token"}).status_code==422


def test_preview_does_not_write(client):
    result=client.post('/api/analyze',json={"title":"Apple reports record profit"}).json()
    assert result["saved"] is False
    assert client.get('/api/overview?mode=replay').json()["counts"]["articles"]==0


def test_import_size_limit_and_csv_formula_escaping(client):
    assert client.post('/api/import',files={"file":("x.csv",b'x'*256001,"text/csv")}).status_code==413
    assert client.post('/api/ingest',json={"title":"=Apple reports profit growth","mode":"replay"}).status_code==200
    assert "'=Apple" in client.get('/api/export?mode=replay&format=csv').text


def test_security_headers_and_no_cache(client):
    response=client.get('/api/health')
    assert response.headers['x-content-type-options']=='nosniff'
    assert response.headers['cache-control']=='no-store'

