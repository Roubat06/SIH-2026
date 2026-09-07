import os
import json
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from .connection import db_session
from .schema import init_schema
from ..utils.security import hash_password
from ..services.features import extract_features_from_tx
from ..services.rules import evaluate_rules
from ..ml.isolation_forest import get_or_train_isolation_forest, score_transaction_anomaly
from ..services.risk import compute_risk_score
from ..rag.documents import KNOWLEDGE_DOCUMENTS

def seed_database():
    init_schema()
    
    with db_session() as conn:
        # Check if already seeded
        user_count = conn.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
        tx_count = conn.execute('SELECT COUNT(*) as c FROM transactions').fetchone()['c']
        if user_count > 0 and tx_count >= 50:
            print('Database already seeded with transactions and users.')
            return
            
        print('Seeding Sentinel database with users, knowledge documents, and realistic Bitcoin transactions...')
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        
        # 1. Users
        admin_id = 'usr_admin_01'
        analyst_id = 'usr_analyst_01'
        
        conn.execute('''
            INSERT OR REPLACE INTO users (id, email, name, role, password_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (admin_id, 'admin@sentinel.sec', 'Security Administrator', 'ADMIN', hash_password('Admin123456!'), now_iso, now_iso))
        
        conn.execute('''
            INSERT OR REPLACE INTO users (id, email, name, role, password_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (analyst_id, 'analyst@sentinel.sec', 'Lead Security Investigator', 'ANALYST', hash_password('Analyst123456!'), now_iso, now_iso))
        
        # 2. Knowledge documents
        for doc in KNOWLEDGE_DOCUMENTS:
            conn.execute('''
                INSERT OR REPLACE INTO knowledge_documents (id, doc_id, title, category, content, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (f'kb_{doc['doc_id']}', doc['doc_id'], doc['title'], doc['category'], doc['content'], json.dumps({}), now_iso))
            
        # 3. Generate Realistic UTXO Graph with Anomaly Cases (100+ rich transactions)
        transactions = []
        base_time = now - timedelta(days=2)
        
        # Pre-known addresses
        known_addrs = [
            'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            'bc1q9v8hp7y5dwh3vkg430mhn6s8d9qwla302dfqwr',
            '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
            '3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy',
            'bc1q8c6fshw2dlwun7ekn9qw0c54jut0n2mgr38pqx',
            'bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrk',
            'bc1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3qccfmv3',
            '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2',
            '34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo'
        ]
        
        # Generator loop for 120 UTXO connected transactions
        for i in range(120):
            tx_hash = hashlib.sha256(f'sentinel_tx_{i}_sih_2026'.encode()).hexdigest()
            tx_time = (base_time + timedelta(minutes=i * 22)).isoformat()
            
            # Create variety of transaction typologies
            if i in [15, 45, 75]:
                # Anomaly: Peel Chain Structuring
                total_val = 850_000_000 # 8.5 BTC
                peel_val = 810_000_000
                change_val = 39_985_000
                fee = 15_000
                inputs = [{'prev_txid': hashlib.sha256(f'prev_{i}'.encode()).hexdigest(), 'prev_vout': 0, 'address': known_addrs[i % len(known_addrs)], 'value_sats': total_val + fee, 'script_type': 'p2wpkh'}]
                outputs = [
                    {'output_index': 0, 'address': f'bc1qpeel_{i}_primary_{secrets.token_hex(4)}', 'value_sats': peel_val, 'script_type': 'p2wpkh'},
                    {'output_index': 1, 'address': f'bc1qpeel_{i}_change_{secrets.token_hex(4)}', 'value_sats': change_val, 'script_type': 'p2wpkh'}
                ]
            elif i in [25, 65, 95]:
                # Anomaly: High Fan-Out / Batch Obfuscation
                total_val = 420_000_000
                fee = 45_000
                out_c = 14
                each = (total_val - fee) // out_c
                inputs = [{'prev_txid': hashlib.sha256(f'prev_{i}'.encode()).hexdigest(), 'prev_vout': 0, 'address': known_addrs[(i+2) % len(known_addrs)], 'value_sats': total_val + fee, 'script_type': 'p2wpkh'}]
                outputs = [{'output_index': j, 'address': f'bc1qfanout_{i}_{j}_{secrets.token_hex(3)}', 'value_sats': each, 'script_type': 'p2wpkh'} for j in range(out_c)]
            elif i in [35, 85]:
                # Anomaly: Dust Attack tracking
                total_val = 25_000_000
                fee = 8_000
                inputs = [{'prev_txid': hashlib.sha256(f'prev_{i}'.encode()).hexdigest(), 'prev_vout': 0, 'address': known_addrs[(i+1) % len(known_addrs)], 'value_sats': total_val + fee, 'script_type': 'p2wpkh'}]
                outputs = [
                    {'output_index': 0, 'address': known_addrs[0], 'value_sats': 546, 'script_type': 'p2wpkh'},
                    {'output_index': 1, 'address': known_addrs[1], 'value_sats': 546, 'script_type': 'p2wpkh'},
                    {'output_index': 2, 'address': known_addrs[2], 'value_sats': 546, 'script_type': 'p2wpkh'},
                    {'output_index': 3, 'address': f'bc1qdust_main_{i}', 'value_sats': total_val - (546*3) - fee, 'script_type': 'p2wpkh'}
                ]
            elif i in [50, 110]:
                # Anomaly: Equal Split CoinJoin
                total_val = 300_000_000
                fee = 20_000
                inputs = [
                    {'prev_txid': hashlib.sha256(f'prev_cj1_{i}'.encode()).hexdigest(), 'prev_vout': 0, 'address': known_addrs[3], 'value_sats': 100_010_000, 'script_type': 'p2wpkh'},
                    {'prev_txid': hashlib.sha256(f'prev_cj2_{i}'.encode()).hexdigest(), 'prev_vout': 0, 'address': known_addrs[4], 'value_sats': 100_010_000, 'script_type': 'p2wpkh'},
                    {'prev_txid': hashlib.sha256(f'prev_cj3_{i}'.encode()).hexdigest(), 'prev_vout': 0, 'address': known_addrs[5], 'value_sats': 100_000_000, 'script_type': 'p2wpkh'}
                ]
                outputs = [
                    {'output_index': 0, 'address': f'bc1qcj_out1_{i}', 'value_sats': 100_000_000, 'script_type': 'p2wpkh'},
                    {'output_index': 1, 'address': f'bc1qcj_out2_{i}', 'value_sats': 100_000_000, 'script_type': 'p2wpkh'},
                    {'output_index': 2, 'address': f'bc1qcj_out3_{i}', 'value_sats': 100_000_000, 'script_type': 'p2wpkh'}
                ]
            else:
                # Normal 1-in 2-out or 2-in 2-out transaction
                val = (10_000_000 * (1 + (i % 12)))
                fee = 1_800 + (i % 5) * 200
                inputs = [{'prev_txid': hashlib.sha256(f'prev_norm_{i}'.encode()).hexdigest(), 'prev_vout': 0, 'address': known_addrs[i % len(known_addrs)], 'value_sats': val + fee, 'script_type': 'p2wpkh'}]
                pay = int(val * 0.7)
                chg = val - pay
                outputs = [
                    {'output_index': 0, 'address': known_addrs[(i + 1) % len(known_addrs)], 'value_sats': pay, 'script_type': 'p2wpkh'},
                    {'output_index': 1, 'address': f'bc1qchange_{i}_{secrets.token_hex(3)}', 'value_sats': chg, 'script_type': 'p2wpkh'}
                ]
                
            in_c = len(inputs)
            out_c = len(outputs)
            tot_in = sum(inp['value_sats'] for inp in inputs)
            tot_out = sum(out['value_sats'] for out in outputs)
            vsize = 140 + out_c * 34 + in_c * 68
            fee_rate = fee / max(vsize, 1)
            
            tx_obj = {
                'txid': tx_hash,
                'inputs': inputs,
                'outputs': outputs,
                'input_count': in_c,
                'output_count': out_c,
                'total_input_sats': tot_in,
                'total_output_sats': tot_out,
                'fee_sats': fee,
                'vsize': vsize,
                'fee_rate': fee_rate,
                'observed_at': tx_time,
                'block_time': tx_time,
                'block_height': 892300 + (i // 5),
                'block_hash': hashlib.sha256(f'block_{892300 + i//5}'.encode()).hexdigest(),
                'confirmed': True
            }
            transactions.append(tx_obj)
            
        # Pre-train Isolation Forest on initial batch
        get_or_train_isolation_forest(transactions)
        
        # Process and store all transactions with rule + ML detection
        for tx in transactions:
            triggered = evaluate_rules(tx)
            anomaly_score, anomaly_label = score_transaction_anomaly(tx)
            risk_score, risk_level, factors = compute_risk_score(tx, triggered, anomaly_score)
            is_flagged = 1 if (risk_score >= 50.0 or len(triggered) > 0) else 0
            
            conn.execute('''
                INSERT OR REPLACE INTO transactions (
                    txid, block_hash, block_height, block_time, observed_at, size_bytes, vsize, weight,
                    version, locktime, fee_sats, fee_rate, total_input_sats, total_output_sats,
                    input_count, output_count, confirmed, risk_score, risk_level, anomaly_score,
                    anomaly_label, is_flagged, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                tx['txid'], tx['block_hash'], tx['block_height'], tx['block_time'], tx['observed_at'],
                tx['vsize'] * 4, tx['vsize'], tx['vsize'] * 4, 2, 0,
                tx['fee_sats'], tx['fee_rate'], tx['total_input_sats'], tx['total_output_sats'],
                tx['input_count'], tx['output_count'], 1,
                risk_score, risk_level, anomaly_score, anomaly_label, is_flagged, 'seed', now_iso
            ))
            
            for inp in tx['inputs']:
                conn.execute('''
                    INSERT OR REPLACE INTO transaction_inputs (id, txid, prev_txid, prev_vout, address, value_sats, sequence, script_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (f"{tx['txid']}_in_{inp['prev_vout']}_{inp['address'][:8]}", tx['txid'], inp['prev_txid'], inp['prev_vout'], inp['address'], inp['value_sats'], 0xffffffff, inp['script_type']))
                
            for out in tx['outputs']:
                conn.execute('''
                    INSERT OR REPLACE INTO transaction_outputs (id, txid, output_index, address, value_sats, script_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (f"{tx['txid']}_out_{out['output_index']}", tx['txid'], out['output_index'], out['address'], out['value_sats'], out['script_type']))
                
            for det in triggered:
                conn.execute('''
                    INSERT OR REPLACE INTO detection_results (id, txid, stage, detector, code, title, feature, observed, operator, threshold, baseline, unit, reason, severity, triggered, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                ''', (f"det_{tx['txid'][:8]}_{det['code']}", tx['txid'], det['stage'], det['detector'], det['code'], det['title'], det.get('feature'), det.get('observed'), det.get('operator'), det.get('threshold'), det.get('baseline'), det.get('unit'), det['reason'], det['severity'], now_iso))
                
            if is_flagged:
                alt_id = f"alt_{tx['txid'][:12]}"
                title = triggered[0]['title'] if triggered else 'Multivariate Statistical Anomaly'
                reason = '; '.join(factors[:2])
                conn.execute('''
                    INSERT OR REPLACE INTO alerts (id, txid, severity, risk_score, anomaly_score, detection_method, title, reason, evidence_json, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'NEW', ?, ?)
                ''', (alt_id, tx['txid'], risk_level, risk_score, anomaly_score, 'Hybrid Detection (Rules + ML)', title, reason, json.dumps({'factors': factors, 'triggered_rules': triggered}), now_iso, now_iso))
                
        # 4. Pre-create 2 Realistic Investigation Cases
        case1_id = 'CAS-2026-0891'
        case1_title = 'Investigation of High-Value Peel Chain Cluster & Obfuscation'
        case1_desc = 'Forensic tracking of multi-stage peel chain structuring exceeding 8.5 BTC across sequential non-custodial wallets.'
        
        conn.execute('''
            INSERT OR REPLACE INTO cases (id, title, description, status, priority, lead_investigator_id, lead_investigator_name, created_at, updated_at)
            VALUES (?, ?, ?, 'INVESTIGATING', 'HIGH', ?, ?, ?, ?)
        ''', (case1_id, case1_title, case1_desc, analyst_id, 'Lead Security Investigator', now_iso, now_iso))
        
        # Link flagged peel transaction
        flagged_txid = transactions[15]['txid']
        conn.execute('''
            INSERT OR REPLACE INTO case_transactions (case_id, txid, added_by, added_at)
            VALUES (?, ?, ?, ?)
        ''', (case1_id, flagged_txid, analyst_id, now_iso))
        
        # Timeline events
        conn.execute('''
            INSERT OR REPLACE INTO investigation_events (id, case_id, txid, event_type, actor_id, actor_name, summary, details_json, created_at)
            VALUES (?, ?, ?, 'ALERT_TRIGGERED', 'SYSTEM', 'Sentinel Detection Engine', 'Heuristic R04 (Peel Chain Structuring) triggered on 8.5 BTC transfer.', ?, ?)
        ''', ('evt_01', case1_id, flagged_txid, json.dumps({'risk_score': 88.0, 'severity': 'HIGH'}), (now - timedelta(hours=6)).isoformat()))
        
        conn.execute('''
            INSERT OR REPLACE INTO investigation_events (id, case_id, txid, event_type, actor_id, actor_name, summary, details_json, created_at)
            VALUES (?, ?, ?, 'CASE_CREATED', ?, 'Lead Security Investigator', 'Investigator opened Case CAS-2026-0891 and attached primary transaction.', ?, ?)
        ''', ('evt_02', case1_id, flagged_txid, analyst_id, json.dumps({}), (now - timedelta(hours=4)).isoformat()))
        
        conn.execute('''
            INSERT OR REPLACE INTO investigation_events (id, case_id, txid, event_type, actor_id, actor_name, summary, details_json, created_at)
            VALUES (?, ?, ?, 'AI_ANALYSIS_REQUESTED', ?, 'Lead Security Investigator', 'AI Security Analyst generated forensic hypothesis and next step recommendations.', ?, ?)
        ''', ('evt_03', case1_id, flagged_txid, analyst_id, json.dumps({}), (now - timedelta(hours=2)).isoformat()))

        
        # Note
        conn.execute('''
            INSERT OR REPLACE INTO investigation_notes (id, case_id, author_id, author_name, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('not_01', case1_id, analyst_id, 'Lead Security Investigator', 'Confirmed 95.3% value retention in primary output with 0.47 BTC peeled off. Downstream address shows recurring peeling behavior.', now_iso))
        
        # Audit Log
        conn.execute('''
            INSERT OR REPLACE INTO audit_logs (id, actor_id, actor_name, action, target_type, target_id, details_json, ip_address, created_at)
            VALUES (?, ?, ?, 'system_database_seeded', 'database', 'sentinel_core', ?, '127.0.0.1', ?)
        ''', ('aud_init', analyst_id, 'Lead Security Investigator', json.dumps({'seeded_tx_count': len(transactions)}), now_iso))
        
        print(f'Successfully seeded database with {len(transactions)} transactions, alerts, cases, and knowledge docs.')
