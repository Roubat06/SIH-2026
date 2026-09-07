from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from ...database.connection import db_session
from ...utils.security import get_current_user

router = APIRouter(prefix='/api/transactions', tags=['Transactions'])

@router.get('')
def list_transactions(
    q: Optional[str] = None,
    risk_level: Optional[str] = None,
    is_flagged: Optional[bool] = None,
    min_sats: Optional[int] = None,
    max_sats: Optional[int] = None,
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user)
):
    with db_session() as conn:
        conditions = []
        params = []
        
        if q:
            q_clean = f'%{q.strip()}%'
            conditions.append('(txid LIKE ? OR block_hash LIKE ? OR txid IN (SELECT txid FROM transaction_outputs WHERE address LIKE ?))')
            params.extend([q_clean, q_clean, q_clean])
            
        if risk_level and risk_level != 'ALL':
            conditions.append('risk_level = ?')
            params.append(risk_level.upper())
            
        if is_flagged is not None:
            conditions.append('is_flagged = ?')
            params.append(1 if is_flagged else 0)
            
        if min_sats is not None:
            conditions.append('total_output_sats >= ?')
            params.append(min_sats)
            
        if max_sats is not None:
            conditions.append('total_output_sats <= ?')
            params.append(max_sats)
            
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        count_query = f"SELECT COUNT(*) as c FROM transactions {where_clause}"
        total = conn.execute(count_query, params).fetchone()['c']
        
        list_query = f"""
            SELECT * FROM transactions
            {where_clause}
            ORDER BY observed_at DESC, risk_score DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        rows = conn.execute(list_query, params).fetchall()
        
        items = [dict(r) for r in rows]
        return {'items': items, 'total': total, 'limit': limit, 'offset': offset}

@router.get('/{txid}')
def get_transaction_detail(txid: str, user: dict = Depends(get_current_user)):
    with db_session() as conn:
        tx = conn.execute('SELECT * FROM transactions WHERE txid = ?', (txid,)).fetchone()
        if not tx:
            raise HTTPException(status_code=404, detail='Transaction not found')
            
        tx_dict = dict(tx)
        inputs = conn.execute('SELECT * FROM transaction_inputs WHERE txid = ?', (txid,)).fetchall()
        outputs = conn.execute('SELECT * FROM transaction_outputs WHERE txid = ? ORDER BY output_index ASC', (txid,)).fetchall()
        detections = conn.execute('SELECT * FROM detection_results WHERE txid = ?', (txid,)).fetchall()
        alerts = conn.execute('SELECT * FROM alerts WHERE txid = ?', (txid,)).fetchall()
        linked_cases = conn.execute('''
            SELECT c.* FROM cases c
            JOIN case_transactions ct ON c.id = ct.case_id
            WHERE ct.txid = ?
        ''', (txid,)).fetchall()
        
        tx_dict['inputs'] = [dict(i) for i in inputs]
        tx_dict['outputs'] = [dict(o) for o in outputs]
        tx_dict['detections'] = [dict(d) for d in detections]
        tx_dict['alerts'] = [dict(a) for a in alerts]
        tx_dict['cases'] = [dict(c) for c in linked_cases]
        
        return tx_dict
