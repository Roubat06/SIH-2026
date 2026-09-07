from fastapi import APIRouter, Depends
from ...database.connection import db_session
from ...utils.security import get_current_user
from ...services.ingestion import fetch_blockchain_tip

router = APIRouter(prefix='/api/dashboard', tags=['Dashboard'])

@router.get('')
def get_dashboard_summary(user: dict = Depends(get_current_user)):
    with db_session() as conn:
        # KPIs
        tx_count = conn.execute("SELECT COUNT(*) as c FROM transactions").fetchone()['c']
        active_alerts = conn.execute("SELECT COUNT(*) as c FROM alerts WHERE status IN ('NEW', 'UNDER_REVIEW', 'ESCALATED')").fetchone()['c']
        high_risk_txs = conn.execute("SELECT COUNT(*) as c FROM transactions WHERE risk_level IN ('HIGH', 'CRITICAL')").fetchone()['c']
        open_cases = conn.execute("SELECT COUNT(*) as c FROM cases WHERE status IN ('OPEN', 'INVESTIGATING', 'ESCALATED')").fetchone()['c']
        anomalies_detected = conn.execute("SELECT COUNT(*) as c FROM transactions WHERE anomaly_score >= 95.0").fetchone()['c']

        
        # Risk distribution
        risk_rows = conn.execute('''
            SELECT risk_level, COUNT(*) as count
            FROM transactions
            GROUP BY risk_level
        ''').fetchall()
        risk_dist = {r['risk_level']: r['count'] for r in risk_rows}
        
        # Alert severity distribution
        alert_rows = conn.execute('''
            SELECT severity, COUNT(*) as count
            FROM alerts
            GROUP BY severity
        ''').fetchall()
        alert_dist = {r['severity']: r['count'] for r in alert_rows}
        
        # Recent Alerts
        recent_alerts = conn.execute('''
            SELECT a.*, t.total_output_sats, t.fee_rate
            FROM alerts a
            JOIN transactions t ON a.txid = t.txid
            ORDER BY a.created_at DESC
            LIMIT 6
        ''').fetchall()
        
        # Recent Open Cases
        recent_cases = conn.execute('''
            SELECT c.*, (SELECT COUNT(*) FROM case_transactions WHERE case_id = c.id) as transaction_count
            FROM cases c
            ORDER BY c.updated_at DESC
            LIMIT 4
        ''').fetchall()
        
        # Traffic time series (last 10 aggregated points)
        traffic_series = conn.execute('''
            SELECT SUBSTR(observed_at, 1, 13) as hour_bucket,
                   COUNT(*) as tx_count,
                   SUM(total_output_sats) as total_volume_sats,
                   AVG(risk_score) as avg_risk
            FROM transactions
            GROUP BY hour_bucket
            ORDER BY hour_bucket DESC
            LIMIT 12
        ''').fetchall()
        traffic_points = [dict(t) for t in reversed(traffic_series)]
        
        tip_info = fetch_blockchain_tip()
        
        return {
            'kpis': {
                'monitored_transactions': tx_count,
                'active_alerts': active_alerts,
                'high_risk_transactions': high_risk_txs,
                'open_cases': open_cases,
                'anomalies_detected': anomalies_detected
            },
            'risk_distribution': {
                'LOW': risk_dist.get('LOW', 0),
                'MEDIUM': risk_dist.get('MEDIUM', 0),
                'HIGH': risk_dist.get('HIGH', 0),
                'CRITICAL': risk_dist.get('CRITICAL', 0)
            },
            'alert_severity_distribution': {
                'LOW': alert_dist.get('LOW', 0),
                'MEDIUM': alert_dist.get('MEDIUM', 0),
                'HIGH': alert_dist.get('HIGH', 0),
                'CRITICAL': alert_dist.get('CRITICAL', 0)
            },
            'traffic_series': traffic_points,
            'recent_alerts': [dict(a) for a in recent_alerts],
            'recent_cases': [dict(c) for c in recent_cases],
            'ingestion_status': {
                'latest_block': tip_info.get('height'),
                'block_hash': tip_info.get('hash'),
                'status': tip_info.get('status'),
                'source': tip_info.get('source'),
                'total_stored': tx_count,
                'last_sync': traffic_points[-1]['hour_bucket'] + ':00' if traffic_points else 'Just now'
            }
        }
