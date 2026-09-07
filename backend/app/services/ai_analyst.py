import os
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
        
        system_instruction = """You are Sentinel AI Security Analyst, an expert Bitcoin blockchain cybersecurity forensic investigator.
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
"""

        rag_context_str = "\n\n".join([f"=== Document: {d['title']} ({d['category']}) ===\n{d['content']}" for d in rag_docs])
        
        evidence_payload = {
            'user_query': prompt,
            'transaction_evidence': tx_data,
            'case_evidence': case_data,
            'retrieved_security_knowledge': rag_context_str
        }
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"EVIDENCE DOSSIER:\n{json.dumps(evidence_payload, indent=2)}\n\nProvide structured forensic evaluation in JSON.",
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
