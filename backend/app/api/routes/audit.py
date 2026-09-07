from fastapi import APIRouter, Depends, Query
from ...database.connection import db_session
from ...utils.security import get_current_user, require_role

router = APIRouter(prefix='/api/audit', tags=['Audit Log'])

@router.get('')
def get_audit_trail(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), user: dict = Depends(get_current_user)):
    with db_session() as conn:
        total = conn.execute('SELECT COUNT(*) as c FROM audit_logs').fetchone()['c']
        rows = conn.execute('SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ? OFFSET ?', (limit, offset)).fetchall()
        return {'items': [dict(r) for r in rows], 'total': total, 'limit': limit, 'offset': offset}
