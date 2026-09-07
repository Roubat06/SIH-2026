import io
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from ..database.connection import db_session

def generate_case_investigation_report(case_id: str) -> Dict[str, Any]:
    with db_session() as conn:
        case = conn.execute('SELECT * FROM cases WHERE id = ?', (case_id,)).fetchone()
        if not case:
            return {'error': 'Case not found'}
        case_dict = dict(case)
        
        # Linked transactions
        txs = conn.execute('''
            SELECT t.* FROM transactions t
            JOIN case_transactions ct ON t.txid = ct.txid
            WHERE ct.case_id = ?
            ORDER BY t.risk_score DESC
        ''', (case_id,)).fetchall()
        tx_list = [dict(t) for t in txs]
        
        # Timeline events
        events = conn.execute('''
            SELECT * FROM investigation_events
            WHERE case_id = ?
            ORDER BY created_at ASC
        ''', (case_id,)).fetchall()
        event_list = [dict(e) for e in events]
        
        # Analyst notes
        notes = conn.execute('''
            SELECT * FROM investigation_notes
            WHERE case_id = ?
            ORDER BY created_at ASC
        ''', (case_id,)).fetchall()
        note_list = [dict(n) for n in notes]
        
        # Alerts associated
        txids = [t['txid'] for t in tx_list]
        alerts = []
        if txids:
            placeholders = ','.join('?' for _ in txids)
            alt_rows = conn.execute(f'''
                SELECT * FROM alerts WHERE txid IN ({placeholders})
                ORDER BY risk_score DESC
            ''', txids).fetchall()
            alerts = [dict(a) for a in alt_rows]
            
        # Compile Report
        report = {
            'report_id': f'REP-{case_id[:8].upper()}-{int(datetime.now().timestamp())}',
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'platform': 'Sentinel AI-Powered Bitcoin Monitoring & Investigation Platform',
            'classification': 'CYBERSECURITY INVESTIGATION EVIDENCE REPORT',
            'case_metadata': case_dict,
            'investigator': case_dict.get('lead_investigator_name', 'Lead Investigator'),
            'summary_statistics': {
                'linked_transactions_count': len(tx_list),
                'active_alerts_count': len(alerts),
                'max_risk_score': max([t['risk_score'] for t in tx_list], default=0.0),
                'highest_severity': 'CRITICAL' if any(t['risk_level'] == 'CRITICAL' for t in tx_list) else ('HIGH' if any(t['risk_level'] == 'HIGH' for t in tx_list) else 'MEDIUM')
            },
            'linked_transactions': tx_list,
            'associated_alerts': alerts,
            'investigation_timeline': event_list,
            'investigator_notes': note_list,
            'detection_methodology': {
                'unsupervised_ml': 'Isolation Forest (120 Estimators, Multivariate topological features)',
                'rule_heuristics': '8 Deterministic Heuristic Detectors (R01-R08)',
                'risk_engine': 'Multi-factor weighted synthesis score (0-100 scale)'
            },
            'legal_ethical_disclaimer': 'This investigative report summarizes algorithmic anomaly detections and topological relationships. Observed network behaviors and heuristic triggers constitute investigative leads and do NOT represent legal proof of illicit intent or ownership attribution.'
        }
        return report
