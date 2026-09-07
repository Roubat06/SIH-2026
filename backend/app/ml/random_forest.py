import os
from typing import List, Dict, Any, Tuple
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from ..services.features import extract_features_from_tx, build_feature_matrix

SUPERVISED_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_models', 'rf_classifier.joblib')

class SupervisedFallbackClassifier:
    """Optional supervised model used ONLY when verified ground-truth labels exist."""
    def __init__(self):
        self.model = None
        self.is_trained = False
        self.model_version = 'sentinel-rf-supervised-v1'
        self._load_if_exists()
        
    def _load_if_exists(self):
        if os.path.exists(SUPERVISED_MODEL_PATH):
            try:
                data = joblib.load(SUPERVISED_MODEL_PATH)
                self.model = data.get('model')
                self.is_trained = True
            except Exception:
                self.is_trained = False
                
    def train(self, transactions: List[Dict[str, Any]], labels: List[int]):
        if len(transactions) < 30 or len(set(labels)) < 2:
            return False
        X = build_feature_matrix(transactions)
        y = np.array(labels, dtype=np.int32)
        
        self.model = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
        self.model.fit(X, y)
        self.is_trained = True
        
        os.makedirs(os.path.dirname(SUPERVISED_MODEL_PATH), exist_ok=True)
        joblib.dump({'model': self.model, 'version': self.model_version}, SUPERVISED_MODEL_PATH)
        return True
        
    def predict_risk_probability(self, tx: Dict[str, Any]) -> float:
        if not self.is_trained or self.model is None:
            return 0.0
        feat = np.array([extract_features_from_tx(tx)], dtype=np.float64)
        probs = self.model.predict_proba(feat)[0]
        return float(probs[1] if len(probs) > 1 else probs[0])
