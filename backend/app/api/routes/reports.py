from fastapi import APIRouter, HTTPException, Depends
from ...utils.security import get_current_user
from ...services.reports import generate_case_investigation_report
from ...services.audit import log_audit_event

router = APIRouter(prefix='/api/reports', tags=['Reports'])

@router.post('/{case_id}')
def create_case_report(case_id: str, user: dict = Depends(get_current_user)):
    report = generate_case_investigation_report(case_id)
    if 'error' in report:
        raise HTTPException(status_code=404, detail=report['error'])
        
    log_audit_event(
        action='investigation_report_generated',
        target_type='case',
        target_id=case_id,
        actor_id=user['id'],
        actor_name=user['name'],
        details={'report_id': report['report_id']}
    )
    return report
