from fastapi import APIRouter, Depends
from ...schemas.models import AIAnalyzeRequest
from ...utils.security import get_current_user
from ...services.ai_analyst import query_ai_security_analyst
from ...services.audit import log_audit_event

router = APIRouter(prefix='/api/ai', tags=['AI Security Analyst'])

@router.post('/analyze')
def ask_ai_analyst(req: AIAnalyzeRequest, user: dict = Depends(get_current_user)):
    response = query_ai_security_analyst(
        prompt=req.prompt,
        txid=req.txid,
        case_id=req.case_id,
        include_rag=req.include_rag
    )
    log_audit_event(
        action='ai_security_analyst_queried',
        target_type='transaction' if req.txid else 'case',
        target_id=req.txid or req.case_id,
        actor_id=user['id'],
        actor_name=user['name'],
        details={'prompt': req.prompt, 'model_used': response.get('model_used')}
    )
    return response
