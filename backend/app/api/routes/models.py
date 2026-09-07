from fastapi import APIRouter, Depends
from ...utils.security import get_current_user
from ...ml.evaluator import get_model_evaluation_report

router = APIRouter(prefix='/api/models', tags=['Model Status & Evaluation'])

@router.get('/status')
def get_model_status(user: dict = Depends(get_current_user)):
    return {
        'isolation_forest': {
            'status': 'ACTIVE',
            'version': 'sentinel-iforest-v2.1',
            'estimators': 120,
            'scoring_percentile_norm': True
        },
        'rule_engine': {
            'status': 'ACTIVE',
            'rules_count': 8,
            'mode': 'Deterministic heuristic analysis'
        },
        'supervised_random_forest': {
            'status': 'STANDBY',
            'is_trained': False,
            'requirement': 'Verified ground truth labels'
        }
    }

@router.get('/evaluation')
def get_model_evaluation(user: dict = Depends(get_current_user)):
    return get_model_evaluation_report()
