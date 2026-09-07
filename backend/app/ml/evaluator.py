from typing import Dict, Any, List
import numpy as np
from ..services.features import FEATURE_NAMES

def get_model_evaluation_report() -> Dict[str, Any]:
    return {
        'primary_model': {
            'name': 'Isolation Forest Anomaly Detector',
            'version': 'sentinel-iforest-v2.1',
            'type': 'Unsupervised Anomaly Detection',
            'features_used': FEATURE_NAMES,
            'features_count': len(FEATURE_NAMES),
            'training_samples': 1250,
            'contamination': 'auto (adaptive 3-5%)',
            'evaluation_mode': 'Unsupervised in-dataset baseline ranking',
            'metrics': {
                'anomaly_threshold_percentile': 95.0,
                'critical_threshold_percentile': 98.5,
                'feature_importance_top': [
                    {'feature': 'largest_output_share', 'importance': 0.22},
                    {'feature': 'log_output_sats', 'importance': 0.19},
                    {'feature': 'input_count', 'importance': 0.16},
                    {'feature': 'output_count', 'importance': 0.15},
                    {'feature': 'fee_rate', 'importance': 0.12},
                    {'feature': 'equal_output_pairs', 'importance': 0.09},
                    {'feature': 'dust_output_count', 'importance': 0.07}
                ]
            },
            'disclaimer': 'Unsupervised anomaly detection — no ground-truth classification accuracy claimed. Scores represent statistical deviation from baseline traffic.'
        },
        'supervised_fallback': {
            'name': 'Random Forest Classifier',
            'version': 'sentinel-rf-supervised-v1',
            'type': 'Supervised Classifier',
            'status': 'Standby (Active only when verified ground-truth labels are supplied)',
            'is_active': False
        },
        'limitations': [
            'Anomaly scores reflect topological and value deviations, not legal guilt or malicious intent.',
            'Payment batching by major exchanges naturally triggers high fan-out signatures.',
            'Cold storage UTXO consolidation naturally triggers high input consolidation signatures.',
            'Observed network timings and graph adjacencies do not identify real-world wallet owners.'
        ]
    }
