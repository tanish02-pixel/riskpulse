from riskpulse import config
from riskpulse.engine import RiskEngine
import pytest


@pytest.mark.skipif(not (config.ROOT / 'runtime/models/finbert/pytorch_model.bin').exists(), reason='Run scripts/setup_model.py first for FinBERT integration checks')
def test_finbert_runs_on_local_weights_and_produces_probabilities():
    engine=RiskEngine('finbert');engine.load_model()
    assert engine.backend=='finbert',engine.model_error
    positive=engine.sentiment('The company reports record profit and strong revenue growth.')
    negative=engine.sentiment('The company faces bankruptcy and major losses.')
    neutral=engine.sentiment('The company publishes its registered office address.')
    assert positive['score']>0 and negative['score']<0 and neutral['label']=='neutral'
    assert sum(positive['probabilities'].values())==pytest.approx(1,abs=1e-5)

