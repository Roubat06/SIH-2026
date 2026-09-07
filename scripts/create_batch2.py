# Batch 2 creator
import os, sys, json, math, re, sqlite3, hashlib, secrets
from datetime import datetime, timezone, timedelta

FILES = {}

FILES['backend/app/services/reports.py'] = '''import io
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
        txs = conn.execute(\'\'\'
            SELECT t.* FROM transactions t
            JOIN case_transactions ct ON t.txid = ct.txid
            WHERE ct.case_id = ?
            ORDER BY t.risk_score DESC
        \'\'\', (case_id,)).fetchall()
        tx_list = [dict(t) for t in txs]
        
        # Timeline events
        events = conn.execute(\'\'\'
            SELECT * FROM investigation_events
            WHERE case_id = ?
            ORDER BY created_at ASC
        \'\'\', (case_id,)).fetchall()
        event_list = [dict(e) for e in events]
        
        # Analyst notes
        notes = conn.execute(\'\'\'
            SELECT * FROM investigation_notes
            WHERE case_id = ?
            ORDER BY created_at ASC
        \'\'\', (case_id,)).fetchall()
        note_list = [dict(n) for n in notes]
        
        # Alerts associated
        txids = [t['txid'] for t in tx_list]
        alerts = []
        if txids:
            placeholders = ','.join('?' for _ in txids)
            alt_rows = conn.execute(f\'\'\'
                SELECT * FROM alerts WHERE txid IN ({placeholders})
                ORDER BY risk_score DESC
            \'\'\', txids).fetchall()
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
'''

FILES['backend/app/rag/documents.py'] = '''from typing import List, Dict, Any

KNOWLEDGE_DOCUMENTS = [
    {
        'doc_id': 'KB-BTC-001',
        'title': 'UTXO Accounting Model & Forensic Implications',
        'category': 'Bitcoin Fundamentals',
        'content': """The Bitcoin blockchain operates on an Unspent Transaction Output (UTXO) model rather than an account-based model. Each transaction consumes one or more existing UTXOs as inputs and creates one or more new UTXOs as outputs. 

Key Investigative Realities:
1. Change Addresses: When an input exceeds the intended payment amount, a new change output is generated back to the sender. This means standard transactions typically have 2 outputs (Payment + Change).
2. Peeling Chains: A common pattern where a large fund is moved step-by-step, peeling off a small payment while transferring the remaining large balance to a fresh address.
3. Multi-Input Clustering Heuristic: When multiple inputs are spent together in a single transaction, common ownership is inferred (Common-Input Ownership Heuristic), except in CoinJoin mixers."""
    },
    {
        'doc_id': 'KB-TYP-002',
        'title': 'Peel Chains & Layering Obfuscation',
        'category': 'Typologies & Laundering Patterns',
        'content': """Peel chains are a classic transaction structuring method used to launder large amounts of cryptocurrency across sequential hops.

Characteristics:
- Asymmetric 2-output structure: One output carries >= 90% of the value (the unpeeled balance), while the second output carries a smaller amount to an exchange or service.
- Rapid succession: Transactions often occur in rapid succession across multiple blocks.
- Risk Interpretation: High transaction volume with constant peeling suggests programmatic movement or funds layering to obscure source of funds."""
    },
    {
        'doc_id': 'KB-TYP-003',
        'title': 'High Fan-Out vs Batch Payouts vs Mixers',
        'category': 'Typologies & Laundering Patterns',
        'content': """High Fan-Out occurs when a transaction has a disproportionately high number of outputs (e.g., >= 10 outputs).

Investigative Differentiation:
1. Legitimate Commercial Batching: Exchanges, mining pools, and payment processors batch hundreds of withdrawal payouts in a single transaction to minimize transaction fees.
2. Mixing / Obfuscation Dispersal: Illicit actors use fan-out to fragment stolen or flagged funds across disposable mule addresses.
3. CoinJoin Mixers: Characterized by multiple inputs from different parties and multiple outputs of EXACTLY equal value (e.g., 0.1 BTC each) to break deterministic transaction graphs."""
    },
    {
        'doc_id': 'KB-TYP-004',
        'title': 'Dusting Attacks and Tracking Markers',
        'category': 'Cyber Threat Intelligence',
        'content': """A Dusting Attack involves sending minuscule amounts of Bitcoin (typically < 1,000 satoshis, known as 'dust') to thousands of public addresses.

Forensic Significance:
- Purpose: Adversaries attempt to deanonymize wallet owners. When the unsuspecting victim spends this dust together with other unspent outputs, the attacker tracks the combined inputs using the multi-input ownership heuristic.
- Defense / Investigation: Investigators should identify unspent dust outputs and flag combined spends that tie previously unconnected clusters together."""
    },
    {
        'doc_id': 'KB-ML-005',
        'title': 'Isolation Forest Anomaly Detection Methodology',
        'category': 'ML & Detection Engine',
        'content': """Sentinel utilizes Isolation Forest as its primary unsupervised anomaly detection engine for high-dimensional Bitcoin transaction vectors.

Methodology:
- Tree Partitioning: Isolates anomalies by randomly selecting a feature and split value. Outlier transactions require significantly fewer random splits to isolate than normal baseline traffic.
- Score Normalization: Sentinel normalizes raw isolation scores into an in-dataset percentile rank (0-100).
- Review Thresholds: Percentiles >= 95.0 generate High Alerts; >= 98.0 generate Critical Alerts.
- Limitation: Unsupervised anomaly scores identify statistical rarity, NOT criminal guilt."""
    },
    {
        'doc_id': 'KB-INV-006',
        'title': 'Standard Operating Procedure (SOP) for Blockchain Investigations',
        'category': 'Investigation Procedures',
        'content': """When an alert is triggered in Sentinel, investigators should follow this standard 5-step SOP:
1. Triage Alert: Review anomaly percentile, triggered heuristic rules, and specific input/output values.
2. Graph Inspection: Open Graph Explorer to analyze 1-hop and 2-hop neighbor nodes (Address -> Transaction -> Address). Check if outputs converge or disperse.
3. Case Association: Assign the flagged transaction to an active investigation case or create a new case.
4. AI Security Analyst Inquiry: Consult AI Analyst with structured evidence for grounded hypotheses and recommended next steps.
5. Evidence Dossier Export: Add investigator notes, verify timeline chronology, and export the official signed investigation report."""
    }
]
'''

FILES['backend/app/rag/embeddings.py'] = '''import math
import re
from typing import List, Dict, Any
import numpy as np

def tokenize(text: str) -> List[str]:
    return re.findall(r'[a-zA-Z0-9_\-]+', text.lower())

class LightweightEmbeddingEngine:
    """Zero-dependency TF-IDF + BM25 lightweight vector engine compatible with all Python 3.13 environments."""
    def __init__(self):
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.doc_vectors: List[np.ndarray] = []
        self.doc_metadata: List[Dict[str, Any]] = []
        
    def fit_transform(self, documents: List[Dict[str, Any]]):
        self.doc_metadata = documents
        num_docs = len(documents)
        df = {}
        doc_tokens_list = []
        
        for doc in documents:
            text = f"{doc.get('title', '')} {doc.get('category', '')} {doc.get('content', '')}"
            tokens = set(tokenize(text))
            doc_tokens_list.append(tokenize(text))
            for t in tokens:
                df[t] = df.get(t, 0) + 1
                
        # Build vocab
        sorted_terms = sorted(df.keys())
        self.vocabulary = {term: idx for idx, term in enumerate(sorted_terms)}
        self.idf = {term: math.log((num_docs + 1) / (df[term] + 1)) + 1.0 for term in sorted_terms}
        
        # Build vectors
        self.doc_vectors = []
        for tokens in doc_tokens_list:
            vec = np.zeros(len(self.vocabulary), dtype=np.float32)
            tf = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            for t, count in tf.items():
                if t in self.vocabulary:
                    idx = self.vocabulary[t]
                    vec[idx] = (count / max(len(tokens), 1)) * self.idf[t]
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            self.doc_vectors.append(vec)
            
    def query(self, query_text: str, top_k: int = 4) -> List[Dict[str, Any]]:
        if not self.doc_vectors or not self.vocabulary:
            return []
            
        tokens = tokenize(query_text)
        query_vec = np.zeros(len(self.vocabulary), dtype=np.float32)
        tf = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        for t, count in tf.items():
            if t in self.vocabulary:
                idx = self.vocabulary[t]
                query_vec[idx] = (count / max(len(tokens), 1)) * self.idf.get(t, 1.0)
                
        norm = np.linalg.norm(query_vec)
        if norm > 0:
            query_vec = query_vec / norm
            
        scores = []
        for idx, dvec in enumerate(self.doc_vectors):
            similarity = float(np.dot(query_vec, dvec))
            scores.append((similarity, self.doc_metadata[idx]))
            
        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for sim, meta in scores[:top_k]:
            results.append({
                'doc_id': meta.get('doc_id'),
                'title': meta.get('title'),
                'category': meta.get('category'),
                'content': meta.get('content'),
                'similarity_score': round(float(sim), 4)
            })
        return results
'''

FILES['backend/app/rag/store.py'] = '''from typing import List, Dict, Any
from .documents import KNOWLEDGE_DOCUMENTS
from .embeddings import LightweightEmbeddingEngine
from ..database.connection import db_session

_engine: LightweightEmbeddingEngine = None

def get_rag_store() -> LightweightEmbeddingEngine:
    global _engine
    if _engine is not None:
        return _engine
        
    _engine = LightweightEmbeddingEngine()
    
    # Load documents from DB or fallback to constants
    docs = []
    try:
        with db_session() as conn:
            rows = conn.execute('SELECT doc_id, title, category, content FROM knowledge_documents').fetchall()
            if rows:
                docs = [dict(r) for r in rows]
    except Exception:
        pass
        
    if not docs:
        docs = KNOWLEDGE_DOCUMENTS
        
    _engine.fit_transform(docs)
    return _engine

def search_security_knowledge(query_text: str, top_k: int = 4) -> List[Dict[str, Any]]:
    store = get_rag_store()
    return store.query(query_text, top_k=top_k)
'''

FILES['backend/app/services/ai_analyst.py'] = '''import os
import json
from typing import Dict, Any, List, Optional
from ..database.connection import db_session
from ..rag.store import search_security_knowledge

def generate_deterministic_analyst_response(
    tx_data: Optional[Dict[str, Any]],
    case_data: Optional[Dict[str, Any]],
    prompt: str,
    rag_docs: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Offline, deterministic expert system fallback when Gemini API key is not present."""
    facts = []
    indications = []
    suggestions = []
    
    if tx_data:
        txid = tx_data.get('txid', 'N/A')
        total_sats = tx_data.get('total_output_sats', 0)
        btc_val = total_sats / 100_000_000
        in_c = tx_data.get('input_count', 0)
        out_c = tx_data.get('output_count', 0)
        risk = tx_data.get('risk_score', 0.0)
        level = tx_data.get('risk_level', 'LOW')
        anomaly = tx_data.get('anomaly_score', 0.0)
        
        facts.append(f'Transaction TXID: {txid}')
        facts.append(f'Transferred Value: {btc_val:.4f} BTC ({total_sats:,} satoshis)')
        facts.append(f'UTXO Structure: {in_c} Inputs -> {out_c} Outputs')
        facts.append(f'Risk Score: {risk}/100 ({level}), Anomaly Percentile: {anomaly}%')
        
        if out_c >= 10:
            indications.append('Elevated output count indicates batch payout or multi-destination funds dispersal.')
        if in_c >= 10:
            indications.append('Elevated input consolidation suggests sweeping of fragmented wallet UTXOs.')
        if risk >= 75.0:
            indications.append('Multi-rule heuristic triggers combined with high Isolation Forest anomaly percentile indicate high deviation from baseline.')
        else:
            indications.append('Transaction metrics reflect moderate behavioral variance within standard network deviation.')
            
        suggestions.append('Inspect connected downstream outputs in the Graph Explorer for secondary fan-out or exchange deposit consolidation.')
        suggestions.append('Verify whether the source address has prior interactions or historical alert records in the workspace.')
        suggestions.append('Attach this transaction and observation notes to an active investigation case.')
    else:
        facts.append('General security knowledge query regarding Bitcoin forensic typologies.')
        indications.append('Retrieved relevant security doctrine and UTXO forensic guidelines from knowledge base.')
        suggestions.append('Apply these standard typologies to specific flagged transactions in the Alert Queue.')
        
    rag_sources = [f"{d.get('title')} ({d.get('category')})" for d in rag_docs]
    
    summary = f"Security Analysis Findings: Flagged transaction exhibits {level} risk ({risk if tx_data else 0}/100) primarily driven by topology and statistical baseline deviation. Forensic review recommended."
    why_it_matters = "Abnormal structural parameters (e.g. peeling, dusting, or unusual consolidation) are common indicators of funds layering, automated script transfers, or tracking countermeasures."
    limitations = "Algorithmic anomaly detection identifies topological and statistical divergence, NOT confirmed illicit ownership. Commercial services and exchanges frequently generate similar patterns."
    
    return {
        'summary': summary,
        'evidence': facts,
        'why_it_matters': why_it_matters,
        'recommended_steps': suggestions,
        'limitations': limitations,
        'facts': facts,
        'model_indications': indications,
        'suggestions': suggestions,
        'model_used': 'Sentinel Deterministic Forensic Engine (Offline Fallback)',
        'rag_sources': rag_sources
    }

def query_ai_security_analyst(
    prompt: str,
    txid: Optional[str] = None,
    case_id: Optional[str] = None,
    include_rag: bool = True
) -> Dict[str, Any]:
    tx_data = None
    case_data = None
    
    with db_session() as conn:
        if txid:
            row = conn.execute('SELECT * FROM transactions WHERE txid = ?', (txid,)).fetchone()
            if row:
                tx_data = dict(row)
                inputs = conn.execute('SELECT * FROM transaction_inputs WHERE txid = ?', (txid,)).fetchall()
                outputs = conn.execute('SELECT * FROM transaction_outputs WHERE txid = ?', (txid,)).fetchall()
                tx_data['inputs'] = [dict(i) for i in inputs]
                tx_data['outputs'] = [dict(o) for o in outputs]
                
        if case_id:
            c_row = conn.execute('SELECT * FROM cases WHERE id = ?', (case_id,)).fetchone()
            if c_row:
                case_data = dict(c_row)
                
    # RAG search
    rag_docs = []
    if include_rag:
        rag_query = f"{prompt} {tx_data.get('risk_level', '') if tx_data else ''} Bitcoin transaction forensics"
        rag_docs = search_security_knowledge(rag_query, top_k=3)
        
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key:
        return generate_deterministic_analyst_response(tx_data, case_data, prompt, rag_docs)
        
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        system_instruction = \"\"\"You are Sentinel AI Security Analyst, an expert Bitcoin blockchain cybersecurity forensic investigator.
You assist human security investigators by analyzing transaction facts, anomaly model scores, heuristic rules, and RAG knowledge.

CRITICAL RULES:
1. NEVER invent or hallucinate transaction facts, amounts, or addresses.
2. Clearly separate:
   - [OBSERVED FACTS]: Concrete data from transaction inputs/outputs/fees.
   - [MODEL INDICATIONS]: Probabilistic/statistical scores from Isolation Forest or Rules.
   - [INVESTIGATIVE SUGGESTIONS]: Actionable steps for human analyst review.
3. NEVER claim that a transaction or address is definitely criminal or belongs to a specific real-world identity.
4. Maintain a disciplined, professional cybersecurity SOC tone.
5. Return your analysis in valid JSON format matching this schema:
{
  "summary": "Brief 2-3 sentence overview",
  "evidence": ["Fact 1", "Fact 2"],
  "why_it_matters": "Why this pattern warrants review",
  "recommended_steps": ["Step 1", "Step 2"],
  "limitations": "Analytical limitations",
  "facts": ["Fact 1", "Fact 2"],
  "model_indications": ["Indication 1"],
  "suggestions": ["Suggestion 1"]
}
\"\"\"

        rag_context_str = "\\n\\n".join([f"=== Document: {d['title']} ({d['category']}) ===\\n{d['content']}" for d in rag_docs])
        
        evidence_payload = {
            'user_query': prompt,
            'transaction_evidence': tx_data,
            'case_evidence': case_data,
            'retrieved_security_knowledge': rag_context_str
        }
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"EVIDENCE DOSSIER:\\n{json.dumps(evidence_payload, indent=2)}\\n\\nProvide structured forensic evaluation in JSON.",
            config={'response_mime_type': 'application/json', 'system_instruction': system_instruction}
        )
        
        parsed = json.loads(response.text)
        parsed['model_used'] = 'Google Gemini 2.5 Flash + Sentinel RAG'
        parsed['rag_sources'] = [f"{d['title']} ({d['category']})" for d in rag_docs]
        return parsed
    except Exception as e:
        print(f"Gemini API call failed or unavailable ({e}), using deterministic fallback.")
        fallback = generate_deterministic_analyst_response(tx_data, case_data, prompt, rag_docs)
        fallback['model_used'] = f'Deterministic Fallback (Gemini API unavailable: {str(e)[:40]})'
        return fallback
'''

FILES['backend/app/database/seed.py'] = '''import os
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
        
        conn.execute(\'\'\'
            INSERT OR REPLACE INTO users (id, email, name, role, password_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        \'\'\', (admin_id, 'admin@sentinel.sec', 'Security Administrator', 'ADMIN', hash_password('Admin123456!'), now_iso, now_iso))
        
        conn.execute(\'\'\'
            INSERT OR REPLACE INTO users (id, email, name, role, password_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        \'\'\', (analyst_id, 'analyst@sentinel.sec', 'Lead Security Investigator', 'ANALYST', hash_password('Analyst123456!'), now_iso, now_iso))
        
        # 2. Knowledge documents
        for doc in KNOWLEDGE_DOCUMENTS:
            conn.execute(\'\'\'
                INSERT OR REPLACE INTO knowledge_documents (id, doc_id, title, category, content, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            \'\'\', (f'kb_{doc[\x27doc_id\x27]}', doc['doc_id'], doc['title'], doc['category'], doc['content'], json.dumps({}), now_iso))
            
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
            
            conn.execute(\'\'\'
                INSERT OR REPLACE INTO transactions (
                    txid, block_hash, block_height, block_time, observed_at, size_bytes, vsize, weight,
                    version, locktime, fee_sats, fee_rate, total_input_sats, total_output_sats,
                    input_count, output_count, confirmed, risk_score, risk_level, anomaly_score,
                    anomaly_label, is_flagged, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            \'\'\', (
                tx['txid'], tx['block_hash'], tx['block_height'], tx['block_time'], tx['observed_at'],
                tx['vsize'] * 4, tx['vsize'], tx['vsize'] * 4, 2, 0,
                tx['fee_sats'], tx['fee_rate'], tx['total_input_sats'], tx['total_output_sats'],
                tx['input_count'], tx['output_count'], 1,
                risk_score, risk_level, anomaly_score, anomaly_label, is_flagged, 'seed', now_iso
            ))
            
            for inp in tx['inputs']:
                conn.execute(\'\'\'
                    INSERT OR REPLACE INTO transaction_inputs (id, txid, prev_txid, prev_vout, address, value_sats, sequence, script_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                \'\'\', (f"{tx['txid']}_in_{inp['prev_vout']}_{inp['address'][:8]}", tx['txid'], inp['prev_txid'], inp['prev_vout'], inp['address'], inp['value_sats'], 0xffffffff, inp['script_type']))
                
            for out in tx['outputs']:
                conn.execute(\'\'\'
                    INSERT OR REPLACE INTO transaction_outputs (id, txid, output_index, address, value_sats, script_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                \'\'\', (f"{tx['txid']}_out_{out['output_index']}", tx['txid'], out['output_index'], out['address'], out['value_sats'], out['script_type']))
                
            for det in triggered:
                conn.execute(\'\'\'
                    INSERT OR REPLACE INTO detection_results (id, txid, stage, detector, code, title, feature, observed, operator, threshold, baseline, unit, reason, severity, triggered, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                \'\'\', (f"det_{tx['txid'][:8]}_{det['code']}", tx['txid'], det['stage'], det['detector'], det['code'], det['title'], det.get('feature'), det.get('observed'), det.get('operator'), det.get('threshold'), det.get('baseline'), det.get('unit'), det['reason'], det['severity'], now_iso))
                
            if is_flagged:
                alt_id = f"alt_{tx['txid'][:12]}"
                title = triggered[0]['title'] if triggered else 'Multivariate Statistical Anomaly'
                reason = '; '.join(factors[:2])
                conn.execute(\'\'\'
                    INSERT OR REPLACE INTO alerts (id, txid, severity, risk_score, anomaly_score, detection_method, title, reason, evidence_json, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'NEW', ?, ?)
                \'\'\', (alt_id, tx['txid'], risk_level, risk_score, anomaly_score, 'Hybrid Detection (Rules + ML)', title, reason, json.dumps({'factors': factors, 'triggered_rules': triggered}), now_iso, now_iso))
                
        # 4. Pre-create 2 Realistic Investigation Cases
        case1_id = 'CAS-2026-0891'
        case1_title = 'Investigation of High-Value Peel Chain Cluster & Obfuscation'
        case1_desc = 'Forensic tracking of multi-stage peel chain structuring exceeding 8.5 BTC across sequential non-custodial wallets.'
        
        conn.execute(\'\'\'
            INSERT OR REPLACE INTO cases (id, title, description, status, priority, lead_investigator_id, lead_investigator_name, created_at, updated_at)
            VALUES (?, ?, ?, 'INVESTIGATING', 'HIGH', ?, ?, ?, ?)
        \'\'\', (case1_id, case1_title, case1_desc, analyst_id, 'Lead Security Investigator', now_iso, now_iso))
        
        # Link flagged peel transaction
        flagged_txid = transactions[15]['txid']
        conn.execute(\'\'\'
            INSERT OR REPLACE INTO case_transactions (case_id, txid, added_by, added_at)
            VALUES (?, ?, ?, ?)
        \'\'\', (case1_id, flagged_txid, analyst_id, now_iso))
        
        # Timeline events
        conn.execute(\'\'\'
            INSERT OR REPLACE INTO investigation_events (id, case_id, txid, event_type, actor_id, actor_name, summary, details_json, created_at)
            VALUES (?, ?, ?, 'ALERT_TRIGGERED', 'SYSTEM', 'Sentinel Detection Engine', 'Heuristic R04 (Peel Chain Structuring) triggered on 8.5 BTC transfer.', ?, ?)
        \'\'\', ('evt_01', case1_id, flagged_txid, json.dumps({'risk_score': 88.0, 'severity': 'HIGH'}), (now - timedelta(hours=6)).isoformat()))
        
        conn.execute(\'\'\'
            INSERT OR REPLACE INTO investigation_events (id, case_id, txid, event_type, actor_id, actor_name, summary, details_json, created_at)
            VALUES (?, ?, ?, 'CASE_CREATED', analyst_id, 'Lead Security Investigator', 'Investigator opened Case CAS-2026-0891 and attached primary transaction.', ?, ?)
        \'\'\', ('evt_02', case1_id, flagged_txid, json.dumps({}), (now - timedelta(hours=4)).isoformat()))
        
        conn.execute(\'\'\'
            INSERT OR REPLACE INTO investigation_events (id, case_id, txid, event_type, actor_id, actor_name, summary, details_json, created_at)
            VALUES (?, ?, ?, 'AI_ANALYSIS_REQUESTED', analyst_id, 'Lead Security Investigator', 'AI Security Analyst generated forensic hypothesis and next step recommendations.', ?, ?)
        \'\'\', ('evt_03', case1_id, flagged_txid, json.dumps({}), (now - timedelta(hours=2)).isoformat()))
        
        # Note
        conn.execute(\'\'\'
            INSERT OR REPLACE INTO investigation_notes (id, case_id, author_id, author_name, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        \'\'\', ('not_01', case1_id, analyst_id, 'Lead Security Investigator', 'Confirmed 95.3% value retention in primary output with 0.47 BTC peeled off. Downstream address shows recurring peeling behavior.', now_iso))
        
        # Audit Log
        conn.execute(\'\'\'
            INSERT OR REPLACE INTO audit_logs (id, actor_id, actor_name, action, target_type, target_id, details_json, ip_address, created_at)
            VALUES (?, ?, ?, 'system_database_seeded', 'database', 'sentinel_core', ?, '127.0.0.1', ?)
        \'\'\', ('aud_init', analyst_id, 'Lead Security Investigator', json.dumps({'seeded_tx_count': len(transactions)}), now_iso))
        
        print(f'Successfully seeded database with {len(transactions)} transactions, alerts, cases, and knowledge docs.')
'''

for path, code in FILES.items():
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(code.strip() + '\n')
    print(f'Generated: {path}')

print('Batch 2 completed successfully')

