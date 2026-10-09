import random
from datetime import datetime, timedelta, timezone
import pytest
from riskpulse.engine import RiskEngine, classify_event, fallback_sentiment
from riskpulse.portfolio import rebalance, bounded_simplex
from riskpulse.feeds import parse_feed, SOURCES
from riskpulse.service import RiskService
from riskpulse.util import fingerprint


def signal(ticker="AAPL", score=.9, confidence=.9, hours=0, id=1):
    return {"id": id, "ticker": ticker, "sentiment_score": score, "confidence": confidence,
        "source_reliability": .9, "published_at": (datetime.now(timezone.utc)-timedelta(hours=hours)).isoformat()}


def test_positive_and_negative_allocation_direction():
    tickers=["AAPL","MSFT"]
    policy={"min_weight":.1,"max_weight":.9,"max_turnover":.5}
    r=rebalance(tickers,{"AAPL":.5,"MSFT":.5},[signal(),signal("MSFT",-.9,id=2)],policy)
    assert r["after"]["AAPL"]>.5 and r["after"]["MSFT"]<.5
    assert sum(r["after"].values())==pytest.approx(1)


def test_neutral_low_confidence_stale_and_global_do_not_tilt():
    tickers=[str(i) for i in range(10)]
    inputs=[signal("0",0),signal("0",.9,.2),signal("0",.9,.9,100),signal(None)]
    r=rebalance(tickers,{t:.1 for t in tickers},inputs)
    assert all(w==pytest.approx(.1) for w in r["after"].values())
    assert r["ignored"]["neutral"]==r["ignored"]["low_confidence"]==r["ignored"]["stale"]==r["ignored"]["global"]==1


def test_half_life_reduces_effect():
    tickers=[str(i) for i in range(10)]
    current={t:.1 for t in tickers}
    fresh=rebalance(tickers,current,[signal("0",hours=0)])
    old=rebalance(tickers,current,[signal("0",hours=24)])
    assert fresh["after"]["0"]>old["after"]["0"]>.1


def test_finbert_neutral_label_with_signed_score_is_not_allocated():
    # Argmax can be neutral even when P(positive) - P(negative) is materially signed.
    neutral = signal("AAPL", -.23, .70)
    neutral["sentiment_label"] = "neutral"
    tickers = ["AAPL", "MSFT"]
    result = rebalance(tickers, {ticker: .5 for ticker in tickers}, [neutral], {"max_weight": .9})
    assert not result["changed"]
    assert result["ignored"]["neutral"] == 1


def test_turnover_limit_is_enforced():
    tickers=[str(i) for i in range(10)]
    r=rebalance(tickers,{t:.1 for t in tickers},[signal("0")],{"max_turnover":.001,"sensitivity":1})
    assert r["turnover"]<=.001+1e-10


def test_random_weight_projection_preserves_limits_and_total():
    rng=random.Random(7)
    for _ in range(200):
        raw=[rng.uniform(-5,5) for _ in range(10)]
        result=bounded_simplex(raw,.02,.18)
        assert sum(result)==pytest.approx(1,abs=1e-10)
        assert all(.02-1e-10<=w<=.18+1e-10 for w in result)


def test_invalid_weight_limits_rejected():
    with pytest.raises(ValueError):bounded_simplex([1,2],.6,.7)


def test_sentiment_negation_and_whole_word_matching():
    assert fallback_sentiment("Apple reports record profit.")["score"]>0
    assert fallback_sentiment("Apple does not report growth.")["score"]<0
    assert fallback_sentiment("The defaulted configuration is a software setting.")["score"]==0


@pytest.mark.parametrize("text,label",[("Global sanctions and war escalate","Geopolitical"),("Credit downgrade after missed repayment","Credit Event"),("Federal Reserve interest rate decision","Macroeconomic"),("Company merger and acquisition","Merger/Acquisition"),("Apple launches a new iPhone","Product Launch")])
def test_required_event_categories(text,label):
    assert classify_event(text)[0]==label


def test_multi_company_sentence_sentiment_is_separated():
    engine=RiskEngine("lexicon")
    signals=engine.analyze("Apple reports record profit. Microsoft faces major losses.")
    by_ticker={s["ticker"]:s for s in signals}
    assert by_ticker["AAPL"]["sentiment_score"]>0
    assert by_ticker["MSFT"]["sentiment_score"]<0


def test_ambiguous_shared_context_is_not_allocated():
    engine=RiskEngine("lexicon")
    signals=engine.analyze("Apple beats Microsoft in a successful launch.")
    for i,s in enumerate(signals):s.update({"id":i,"published_at":datetime.now(timezone.utc).isoformat()})
    r=rebalance(["AAPL","MSFT"],{"AAPL":.5,"MSFT":.5},signals,{"max_weight":.9})
    assert r["ignored"]["shared_context"]==2 and not r["changed"]


def test_fingerprint_removes_format_noise():
    assert fingerprint("Apple: Reports GROWTH!")==fingerprint("apple reports growth")


def test_rss_and_atom_are_supported():
    rss=b'<rss version="2.0"><channel><item><title>Microsoft reports growth</title><description>Revenue rises</description><pubDate>Thu, 08 Oct 2026 10:00:00 GMT</pubDate><link>https://example.com/1</link></item></channel></rss>'
    atom=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Apple launches new product</title><summary>Strong demand</summary><updated>2026-10-08T10:00:00Z</updated><link href="https://example.com/2"/></entry></feed>'
    assert parse_feed(rss,next(s for s in SOURCES if s['id']=='microsoft_blog'))[0]["source_type"]=="company_announcement"
    assert parse_feed(atom,SOURCES[1])[0]["title"]=="Apple launches new product"


def test_html_error_page_does_not_become_a_signal():
    with pytest.raises(ValueError):parse_feed(b'<html>Access Denied</html>',SOURCES[1])


def test_service_dedup_replay_separation_and_restart(tmp_path):
    path=tmp_path/"app.db"
    service=RiskService(path,"lexicon")
    r=service.replay(True)
    assert r["ingested"]==12
    before=service.store.current("replay",service.tickers)
    assert before["NVDA"]>.1 and before["JPM"]<.1
    assert all(v==pytest.approx(.1) for v in service.store.current("live",service.tickers).values())
    assert service.replay()["ingested"]==0
    restarted=RiskService(path,"lexicon")
    assert restarted.store.current("replay",service.tickers)==before


def test_replay_reset_preserves_live_records(tmp_path):
    service=RiskService(tmp_path/"app.db","lexicon")
    service.ingest({"title":"Apple reports record profit in live source", "source":"Test news", "source_type":"financial_news", "published_at":datetime.now(timezone.utc).isoformat(),"mode":"live"})
    service.replay(True)
    service.store.reset_replay()
    assert service.store.counts("live")["articles"]==1

