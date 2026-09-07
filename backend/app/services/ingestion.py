import os
import json
import time
import requests
import secrets
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from ..database.connection import db_session
from .features import extract_features_from_tx
from .rules import evaluate_rules
from ..ml.isolation_forest import score_transaction_anomaly
from .risk import compute_risk_score
from .audit import log_audit_event

BITCOIN_API_URL = os.getenv('BITCOIN_API_URL', 'https://blockstream.info/api').rstrip('/')

def fetch_blockchain_tip() -> Dict[str, Any]:
    try:
        resp = requests.get(f'{BITCOIN_API_URL}/blocks/tip/height', timeout=1.5)
        if resp.status_code == 200:
            height = int(resp.text.strip())
            h_resp = requests.get(f'{BITCOIN_API_URL}/blocks/tip/hash', timeout=1.5)
            tip_hash = h_resp.text.strip() if h_resp.status_code == 200 else ''
            return {'height': height, 'hash': tip_hash, 'status': 'connected', 'source': 'Blockstream Esplora API'}
    except Exception:
        pass

    return {'height': 892400, 'hash': '00000000000000000002ab458c89de012489cbe0', 'status': 'offline_fallback', 'source': 'Local Fallback / Seed Cache'}

def process_and_store_transactions(raw_transactions: List[Dict[str, Any]], source: str = 'live_api') -> Tuple[int, int]:
    inserted_count = 0
    alerts_created = 0
    now_iso = datetime.now(timezone.utc).isoformat()
    
    with db_session() as conn:
        for raw in raw_transactions:
            txid = raw.get('txid')
            if not txid:
                continue
                
            existing = conn.execute('SELECT txid FROM transactions WHERE txid = ?', (txid,)).fetchone()
            if existing:
                continue
                
            inputs = raw.get('inputs', [])
            outputs = raw.get('outputs', [])
            
            in_count = len(inputs)
            out_count = len(outputs)
            
            tot_in = sum(i.get('value_sats', 0) for i in inputs)
            tot_out = sum(o.get('value_sats', 0) for o in outputs)
            
            fee = raw.get('fee_sats', max(0, tot_in - tot_out) if tot_in > tot_out else 0)
            vsize = raw.get('vsize', 140 + out_count * 34 + in_count * 68)
            fee_rate = raw.get('fee_rate', fee / max(vsize, 1))
            
            tx_dict = {
                'txid': txid,
                'inputs': inputs,
                'outputs': outputs,
                'input_count': in_count,
                'output_count': out_count,
                'total_input_sats': tot_in,
                'total_output_sats': tot_out,
                'fee_sats': fee,
                'vsize': vsize,
                'fee_rate': fee_rate,
                'observed_at': raw.get('observed_at', now_iso),
                'block_time': raw.get('block_time', now_iso),
                'block_height': raw.get('block_height', 892400),
                'block_hash': raw.get('block_hash', '')
            }
            
            # 1. Rule Engine
            triggered = evaluate_rules(tx_dict)
            
            # 2. Isolation Forest
            anomaly_score, anomaly_label = score_transaction_anomaly(tx_dict)
            
            # 3. Risk Engine
            risk_score, risk_level, factors = compute_risk_score(tx_dict, triggered, anomaly_score)
            is_flagged = 1 if (risk_score >= 50.0 or len(triggered) > 0) else 0
            
            # Insert transaction
            conn.execute('''
                INSERT INTO transactions (
                    txid, block_hash, block_height, block_time, observed_at, size_bytes, vsize, weight,
                    version, locktime, fee_sats, fee_rate, total_input_sats, total_output_sats,
                    input_count, output_count, confirmed, risk_score, risk_level, anomaly_score,
                    anomaly_label, is_flagged, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                txid, raw.get('block_hash'), raw.get('block_height', 892400),
                raw.get('block_time', now_iso), raw.get('observed_at', now_iso),
                raw.get('size_bytes', vsize * 4), vsize, vsize * 4,
                raw.get('version', 2), raw.get('locktime', 0),
                fee, fee_rate, tot_in, tot_out, in_count, out_count,
                1 if raw.get('confirmed', True) else 0,
                risk_score, risk_level, anomaly_score, anomaly_label, is_flagged, source, now_iso
            ))
            
            # Insert inputs & outputs
            for idx, inp in enumerate(inputs):
                inp_id = f'{txid}_in_{idx}'
                conn.execute('''
                    INSERT INTO transaction_inputs (id, txid, prev_txid, prev_vout, address, value_sats, sequence, script_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (inp_id, txid, inp.get('prev_txid'), inp.get('prev_vout', 0), inp.get('address'), inp.get('value_sats', 0), inp.get('sequence', 0xffffffff), inp.get('script_type', 'p2wpkh')))
                
            for idx, out in enumerate(outputs):
                out_id = f'{txid}_out_{idx}'
                conn.execute('''
                    INSERT INTO transaction_outputs (id, txid, output_index, address, value_sats, script_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (out_id, txid, idx, out.get('address'), out.get('value_sats', 0), out.get('script_type', 'p2wpkh')))
                
            # Insert detection results
            for det in triggered:
                det_id = f'det_{secrets.token_hex(8)}'
                conn.execute('''
                    INSERT INTO detection_results (id, txid, stage, detector, code, title, feature, observed, operator, threshold, baseline, unit, reason, severity, triggered, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                ''', (det_id, txid, det['stage'], det['detector'], det['code'], det['title'], det.get('feature'), det.get('observed'), det.get('operator'), det.get('threshold'), det.get('baseline'), det.get('unit'), det['reason'], det['severity'], now_iso))
                
            # Create alert if flagged
            if is_flagged:
                alert_id = f'alt_{secrets.token_hex(8)}'
                main_title = triggered[0]['title'] if triggered else 'Multivariate Statistical Anomaly'
                main_reason = '; '.join(factors[:2])
                conn.execute('''
                    INSERT INTO alerts (id, txid, severity, risk_score, anomaly_score, detection_method, title, reason, evidence_json, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'NEW', ?, ?)
                ''', (alert_id, txid, risk_level, risk_score, anomaly_score, 'Hybrid Detection (Rules + ML)', main_title, main_reason, json.dumps({'factors': factors, 'triggered_rules': triggered}), now_iso, now_iso))
                alerts_created += 1
                
            inserted_count += 1
            
    log_audit_event(action='bitcoin_data_ingested', target_type='ingestion', details={'inserted_count': inserted_count, 'alerts_created': alerts_created, 'source': source})
    return inserted_count, alerts_created
