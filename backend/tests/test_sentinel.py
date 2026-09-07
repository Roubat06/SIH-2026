import unittest
import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.database.schema import init_schema
from app.database.seed import seed_database
from app.services.features import extract_features_from_tx
from app.services.rules import evaluate_rules
from app.ml.isolation_forest import score_transaction_anomaly
from app.services.risk import compute_risk_score
from app.rag.store import search_security_knowledge


def test_health_check(client):
    resp = client.get('/api/health')
    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'healthy'
    assert 'SQLite3' in data['database']

def test_dashboard_summary(client):
    resp = client.get('/api/dashboard')
    assert resp.status_code == 200
    data = resp.json()
    assert 'kpis' in data
    assert data['kpis']['monitored_transactions'] >= 100
    assert 'risk_distribution' in data
    assert 'traffic_series' in data

def test_transactions_list_and_detail(client):
    resp = client.get('/api/transactions?limit=10')
    assert resp.status_code == 200
    data = resp.json()
    assert 'items' in data
    assert len(data['items']) > 0
    
    first_txid = data['items'][0]['txid']
    detail_resp = client.get(f'/api/transactions/{first_txid}')
    assert detail_resp.status_code == 200
    tx_detail = detail_resp.json()
    assert tx_detail['txid'] == first_txid
    assert 'inputs' in tx_detail
    assert 'outputs' in tx_detail

def test_alerts_list_and_update(client):
    resp = client.get('/api/alerts?limit=5')
    assert resp.status_code == 200
    data = resp.json()
    assert 'items' in data
    assert len(data['items']) > 0
    
    first_alert = data['items'][0]
    alert_id = first_alert['id']
    
    # Update status
    update_resp = client.post(f'/api/alerts/{alert_id}/status', json={'status': 'UNDER_REVIEW', 'note': 'Testing triage'})
    assert update_resp.status_code == 200
    assert update_resp.json()['status'] == 'UNDER_REVIEW'

def test_cases_workflow(client):
    # Create Case
    create_resp = client.post('/api/cases', json={
        'title': 'Test Case for Automated Verification',
        'description': 'Integration testing case',
        'priority': 'HIGH',
        'txids': []
    })
    assert create_resp.status_code == 200
    case_data = create_resp.json()
    case_id = case_data['id']
    
    # Add Note
    note_resp = client.post(f'/api/cases/{case_id}/notes', json={'note': 'Test forensic note added'})
    assert note_resp.status_code == 200
    
    # Get Case Details
    detail_resp = client.get(f'/api/cases/{case_id}')
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail['title'] == 'Test Case for Automated Verification'
    assert len(detail['notes']) >= 1

def test_graph_endpoint(client):
    resp = client.get('/api/transactions?limit=1')
    txid = resp.json()['items'][0]['txid']
    
    graph_resp = client.get(f'/api/graph/{txid}')
    assert graph_resp.status_code == 200
    graph_data = graph_resp.json()
    assert 'elements' in graph_data
    assert len(graph_data['elements']['nodes']) >= 1

def test_rag_knowledge_search(client):
    rag_resp = client.post('/api/rag/search', json={'query': 'peel chain structuring', 'limit': 3})
    assert rag_resp.status_code == 200
    rag_data = rag_resp.json()
    assert 'results' in rag_data
    assert len(rag_data['results']) > 0
    assert 'Peel' in rag_data['results'][0]['title'] or 'UTXO' in rag_data['results'][0]['title']

def test_ai_security_analyst_offline_fallback(client):
    tx_resp = client.get('/api/transactions?limit=1')
    txid = tx_resp.json()['items'][0]['txid']
    
    ai_resp = client.post('/api/ai/analyze', json={
        'txid': txid,
        'prompt': 'Why was this transaction flagged and what should I investigate next?',
        'include_rag': True
    })
    assert ai_resp.status_code == 200
    ai_data = ai_resp.json()
    assert 'summary' in ai_data
    assert 'facts' in ai_data
    assert 'recommended_steps' in ai_data
    assert 'limitations' in ai_data

def test_report_generation(client):
    cases_resp = client.get('/api/cases')
    case_id = cases_resp.json()[0]['id']
    
    rep_resp = client.post(f'/api/reports/{case_id}')
    assert rep_resp.status_code == 200
    rep_data = rep_resp.json()
    assert 'report_id' in rep_data
    assert 'classification' in rep_data
    assert 'linked_transactions' in rep_data

def test_manual_sync_ingestion(client):
    sync_resp = client.post('/api/bitcoin/sync', json={'count': 5, 'use_live_api': False})
    assert sync_resp.status_code == 200
    sync_data = sync_resp.json()
    assert sync_data['status'] == 'success'
    assert sync_data['transactions_processed'] == 5

def test_audit_logs(client):
    audit_resp = client.get('/api/audit?limit=10')
    assert audit_resp.status_code == 200
    audit_data = audit_resp.json()
    assert 'items' in audit_data
    assert len(audit_data['items']) > 0

def test_rule_and_ml_detection_logic():
    # Test High Value & Fan-Out Rule
    test_tx = {
        'txid': 'test_tx_001',
        'input_count': 1,
        'output_count': 12,
        'total_input_sats': 600_000_000,
        'total_output_sats': 599_980_000,
        'fee_sats': 20_000,
        'vsize': 250,
        'fee_rate': 80.0,
        'outputs': [{'value_sats': 49_998_333} for _ in range(12)]
    }
    
    features = extract_features_from_tx(test_tx)
    assert len(features) == 14
    
    triggered = evaluate_rules(test_tx)
    rule_codes = [r['code'] for r in triggered]
    assert 'high_transaction_value' in rule_codes
    assert 'high_fan_out' in rule_codes
    
    anomaly_score, label = score_transaction_anomaly(test_tx)
    assert 0.0 <= anomaly_score <= 100.0
    
    risk_score, level, factors = compute_risk_score(test_tx, triggered, anomaly_score)
    assert level in ['HIGH', 'CRITICAL']
    assert len(factors) >= 2

