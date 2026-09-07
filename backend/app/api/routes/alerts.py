from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from ...database.connection import db_session
from ...utils.security import get_current_user
from ...schemas.models import AlertStatusUpdate
from ...services.audit import log_audit_event
from datetime import datetime, timezone

router = APIRouter(prefix='/api/alerts', tags=['Alerts'])

@router.get('')
def list_alerts(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user)
):
    with db_session() as conn:
        conditions = []
        params = []
        
        if severity and severity != 'ALL':
            conditions.append('a.severity = ?')
            params.append(severity.upper())
            
        if status and status != 'ALL':
            conditions.append('a.status = ?')
            params.append(status.upper())
            
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        count_q = f"SELECT COUNT(*) as c FROM alerts a {where_clause}"
        total = conn.execute(count_q, params).fetchone()['c']
        
        q = f"""
            SELECT a.*, t.total_output_sats, t.input_count, t.output_count, t.fee_rate, t.observed_at
            FROM alerts a
            JOIN transactions t ON a.txid = t.txid
            {where_clause}
            ORDER BY a.risk_score DESC, a.created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        rows = conn.execute(q, params).fetchall()
        
        return {'items': [dict(r) for r in rows], 'total': total, 'limit': limit, 'offset': offset}

@router.get('/{alert_id}')
def get_alert_detail(alert_id: str, user: dict = Depends(get_current_user)):
    with db_session() as conn:
        alert = conn.execute('SELECT * FROM alerts WHERE id = ?', (alert_id,)).fetchone()
        if not alert:
            raise HTTPException(status_code=404, detail='Alert not found')
        a_dict = dict(alert)
        tx = conn.execute('SELECT * FROM transactions WHERE txid = ?', (alert['txid'],)).fetchone()
        detections = conn.execute('SELECT * FROM detection_results WHERE txid = ?', (alert['txid'],)).fetchall()
        a_dict['transaction'] = dict(tx) if tx else None
        a_dict['detections'] = [dict(d) for d in detections]
        return a_dict

@router.post('/{alert_id}/status')
def update_alert_status(alert_id: str, update: AlertStatusUpdate, user: dict = Depends(get_current_user)):
    now_iso = datetime.now(timezone.utc).isoformat()
    valid_statuses = {'NEW', 'UNDER_REVIEW', 'ESCALATED', 'RESOLVED', 'FALSE_POSITIVE'}
    status_upper = update.status.upper()
    if status_upper not in valid_statuses:
        raise HTTPException(status_code=400, detail=f'Invalid alert status. Must be one of {valid_statuses}')
        
    with db_session() as conn:
        alert = conn.execute('SELECT id, txid FROM alerts WHERE id = ?', (alert_id,)).fetchone()
        if not alert:
            raise HTTPException(status_code=404, detail='Alert not found')
            
        conn.execute('UPDATE alerts SET status = ?, updated_at = ? WHERE id = ?', (status_upper, now_iso, alert_id))
        log_audit_event(
            action='alert_status_updated',
            target_type='alert',
            target_id=alert_id,
            actor_id=user['id'],
            actor_name=user['name'],
            details={'new_status': status_upper, 'note': update.note},
            conn=conn
        )
        return {'message': f'Alert status updated to {status_upper}', 'alert_id': alert_id, 'status': status_upper}

