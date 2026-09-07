from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from ...database.connection import db_session
from ...utils.security import get_current_user
from ...schemas.models import CaseCreate, CaseNoteCreate, CaseResponse
from ...services.audit import log_audit_event
import secrets
from datetime import datetime, timezone

router = APIRouter(prefix='/api/cases', tags=['Investigations'])

@router.get('')
def list_cases(status: Optional[str] = None, user: dict = Depends(get_current_user)):
    with db_session() as conn:
        q = """
            SELECT c.*, (SELECT COUNT(*) FROM case_transactions WHERE case_id = c.id) as transaction_count
            FROM cases c
        """
        params = []
        if status and status != 'ALL':
            q += " WHERE c.status = ?"
            params.append(status.upper())
        q += " ORDER BY c.updated_at DESC"
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]

@router.post('', response_model=CaseResponse)
def create_case(case_in: CaseCreate, user: dict = Depends(get_current_user)):
    now_iso = datetime.now(timezone.utc).isoformat()
    case_id = f'CAS-2026-{secrets.token_hex(3).upper()}'
    
    with db_session() as conn:
        conn.execute('''
            INSERT INTO cases (id, title, description, status, priority, lead_investigator_id, lead_investigator_name, created_at, updated_at)
            VALUES (?, ?, ?, 'OPEN', ?, ?, ?, ?, ?)
        ''', (case_id, case_in.title, case_in.description, case_in.priority.upper(), user['id'], user['name'], now_iso, now_iso))
        
        for txid in case_in.txids:
            conn.execute('INSERT OR IGNORE INTO case_transactions (case_id, txid, added_by, added_at) VALUES (?, ?, ?, ?)', (case_id, txid, user['id'], now_iso))
            conn.execute('''
                INSERT INTO investigation_events (id, case_id, txid, event_type, actor_id, actor_name, summary, created_at)
                VALUES (?, ?, ?, 'TRANSACTION_ATTACHED', ?, ?, 'Transaction added to investigation case.', ?)
            ''', (f'evt_{secrets.token_hex(6)}', case_id, txid, user['id'], user['name'], now_iso))
            
        log_audit_event(action='case_created', target_type='case', target_id=case_id, actor_id=user['id'], actor_name=user['name'], details={'title': case_in.title}, conn=conn)
        
        return CaseResponse(
            id=case_id,
            title=case_in.title,
            description=case_in.description,
            status='OPEN',
            priority=case_in.priority.upper(),
            lead_investigator_id=user['id'],
            lead_investigator_name=user['name'],
            transaction_count=len(case_in.txids),
            created_at=now_iso,
            updated_at=now_iso
        )

@router.get('/{case_id}')
def get_case_detail(case_id: str, user: dict = Depends(get_current_user)):
    with db_session() as conn:
        case = conn.execute('SELECT * FROM cases WHERE id = ?', (case_id,)).fetchone()
        if not case:
            raise HTTPException(status_code=404, detail='Case not found')
            
        c_dict = dict(case)
        txs = conn.execute('''
            SELECT t.* FROM transactions t
            JOIN case_transactions ct ON t.txid = ct.txid
            WHERE ct.case_id = ?
            ORDER BY t.risk_score DESC
        ''', (case_id,)).fetchall()
        
        timeline = conn.execute('SELECT * FROM investigation_events WHERE case_id = ? ORDER BY created_at DESC', (case_id,)).fetchall()
        notes = conn.execute('SELECT * FROM investigation_notes WHERE case_id = ? ORDER BY created_at DESC', (case_id,)).fetchall()
        
        c_dict['transactions'] = [dict(t) for t in txs]
        c_dict['timeline'] = [dict(e) for e in timeline]
        c_dict['notes'] = [dict(n) for n in notes]
        return c_dict

@router.post('/{case_id}/notes')
def add_case_note(case_id: str, note_in: CaseNoteCreate, user: dict = Depends(get_current_user)):
    now_iso = datetime.now(timezone.utc).isoformat()
    note_id = f'not_{secrets.token_hex(6)}'
    
    with db_session() as conn:
        case = conn.execute('SELECT id FROM cases WHERE id = ?', (case_id,)).fetchone()
        if not case:
            raise HTTPException(status_code=404, detail='Case not found')
            
        conn.execute('INSERT INTO investigation_notes (id, case_id, author_id, author_name, note, created_at) VALUES (?, ?, ?, ?, ?, ?)', (note_id, case_id, user['id'], user['name'], note_in.note, now_iso))
        conn.execute('UPDATE cases SET updated_at = ? WHERE id = ?', (now_iso, case_id))
        
        conn.execute('''
            INSERT INTO investigation_events (id, case_id, event_type, actor_id, actor_name, summary, created_at)
            VALUES (?, ?, 'NOTE_ADDED', ?, ?, 'Investigator added new forensic observation note.', ?)
        ''', (f'evt_{secrets.token_hex(6)}', case_id, user['id'], user['name'], now_iso))
        
        log_audit_event(action='case_note_added', target_type='case', target_id=case_id, actor_id=user['id'], actor_name=user['name'], conn=conn)
        return {'message': 'Note added successfully', 'note_id': note_id, 'created_at': now_iso}

@router.post('/{case_id}/transactions/{txid}')
def attach_transaction_to_case(case_id: str, txid: str, user: dict = Depends(get_current_user)):
    now_iso = datetime.now(timezone.utc).isoformat()
    with db_session() as conn:
        case = conn.execute('SELECT id FROM cases WHERE id = ?', (case_id,)).fetchone()
        if not case:
            raise HTTPException(status_code=404, detail='Case not found')
            
        conn.execute('INSERT OR IGNORE INTO case_transactions (case_id, txid, added_by, added_at) VALUES (?, ?, ?, ?)', (case_id, txid, user['id'], now_iso))
        conn.execute('UPDATE cases SET updated_at = ? WHERE id = ?', (now_iso, case_id))
        
        conn.execute('''
            INSERT INTO investigation_events (id, case_id, txid, event_type, actor_id, actor_name, summary, created_at)
            VALUES (?, ?, ?, 'TRANSACTION_ATTACHED', ?, ?, 'Transaction linked to investigation.', ?)
        ''', (f'evt_{secrets.token_hex(6)}', case_id, txid, user['id'], user['name'], now_iso))
        
        log_audit_event(action='transaction_linked_to_case', target_type='case', target_id=case_id, actor_id=user['id'], actor_name=user['name'], details={'txid': txid}, conn=conn)
        return {'message': f'Transaction {txid} linked to case {case_id}'}

