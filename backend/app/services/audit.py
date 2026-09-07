import json
import secrets
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from ..database.connection import db_session

def log_audit_event(
    action: str,
    target_type: str = None,
    target_id: str = None,
    actor_id: str = 'usr_analyst_01',
    actor_name: str = 'Lead Security Investigator',
    details: Dict[str, Any] = None,
    ip_address: str = '127.0.0.1',
    conn = None
):
    audit_id = f'aud_{secrets.token_hex(8)}'
    now = datetime.now(timezone.utc).isoformat()
    det_json = json.dumps(details or {})
    
    try:
        if conn is not None:
            conn.execute('''
                INSERT INTO audit_logs (id, actor_id, actor_name, action, target_type, target_id, details_json, ip_address, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (audit_id, actor_id, actor_name, action, target_type, target_id, det_json, ip_address, now))
        else:
            with db_session() as c:
                c.execute('''
                    INSERT INTO audit_logs (id, actor_id, actor_name, action, target_type, target_id, details_json, ip_address, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (audit_id, actor_id, actor_name, action, target_type, target_id, det_json, ip_address, now))
    except Exception as e:
        print(f'Audit log error: {e}')

