import math
import os
import joblib
from bisect import bisect_left, bisect_right
from typing import List, Dict, Any, Tuple
import numpy as np
from sklearn.ensemble import IsolationForest
from ..services.features import extract_features_from_tx, build_feature_matrix, FEATURE_NAMES

MODEL_VERSION = 'sentinel-iforest-v2.1'
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_models', 'iforest.joblib')

_cached_model = None
_cached_scores = []

def get_or_train_isolation_forest(training_samples: List[Dict[str, Any]] = None) -> IsolationForest:
    global _cached_model, _cached_scores
    if _cached_model is not None:
        return _cached_model
        
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    if os.path.exists(MODEL_PATH):
        try:
            saved = joblib.load(MODEL_PATH)
            _cached_model = saved.get('model')
            _cached_scores = saved.get('scores', [])
            if _cached_model is not None:
                return _cached_model
        except Exception:
            pass
            
    # Train new model
    if not training_samples or len(training_samples) < 20:
        # Create synthetic baseline
        synth = []
        for i in range(100):
            synth.append({
                'input_count': 1 if i % 4 != 0 else 2,
                'output_count': 2,
                'total_output_sats': 5_000_000 * (1 + (i % 20)),
                'fee_sats': 1500 + i * 10,
                'vsize': 140 + (i % 3) * 30,
                'fee_rate': 12.0 + (i % 15)
            })
        X = build_feature_matrix(synth)
    else:
        X = build_feature_matrix(training_samples)
        
    model = IsolationForest(
        n_estimators=100,
        contamination='auto',
        random_state=42,
        n_jobs=1
    )
    model.fit(X)

    
    raw_scores = -model.score_samples(X)
    _cached_scores = sorted(raw_scores.tolist())
    _cached_model = model
    
    try:
        joblib.dump({'model': model, 'scores': _cached_scores, 'version': MODEL_VERSION}, MODEL_PATH)
    except Exception:
        pass
        
    return _cached_model

def score_transaction_anomaly(tx: Dict[str, Any], model: IsolationForest = None) -> Tuple[float, int]:
    global _cached_scores
    if model is None:
        model = get_or_train_isolation_forest()
        
    feat = extract_features_from_tx(tx)
    X = np.array([feat], dtype=np.float64)
    
    raw_score = float(-model.score_samples(X)[0])
    
    if _cached_scores:
        pos_l = bisect_left(_cached_scores, raw_score)
        pos_r = bisect_right(_cached_scores, raw_score)
        percentile = round(100.0 * (pos_l + 0.5 * (pos_r - pos_l)) / len(_cached_scores), 1)
    else:
        percentile = round(min(100.0, max(0.0, (raw_score + 0.5) * 100.0)), 1)
        
    label = 1 if percentile < 95.0 else -1
    return float(percentile), int(label)
