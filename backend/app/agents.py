"""Multi-Agent Investigation Workflow orchestrated with LangGraph and grounded with Gemini.

Deterministic ML models, detection rules, risk scoring, and graph queries execute
in specialized nodes. The AI Security Analyst synthesizes verified facts and RAG context.
Never invents facts or attributes criminal activity.
"""
from __future__ import annotations
import os
import json
import logging
from typing import Any, TypedDict
from datetime import datetime, timezone

import numpy as np
import faiss
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)

# --- RAG Knowledge Base for Bitcoin Blockchain Investigation ---
BITCOIN_SECURITY_KNOWLEDGE = [
    {
        "id": "kb_peeling_chains",
        "title": "Peeling Chain Patterns & Change Heuristics",
        "content": (
            "A peeling chain is a transaction sequence where a single input address spends into two outputs: "
            "one small payment output and one larger change output that is immediately spent in a subsequent transaction. "
            "In forensic investigation, peeling chains frequently indicate automated batch payment processing, "
            "mixing services, or layered fund distribution. Change outputs typically match the input address script type "
            "or exhibit decimal asymmetry compared to round-number payment amounts."
        ),
        "keywords": ["peeling", "change", "hop", "split", "asymmetry", "chain", "sweep"],
    },
    {
        "id": "kb_fan_in_out",
        "title": "UTXO Consolidation (Fan-In) and Dispersion (Fan-Out)",
        "content": (
            "High input fan-in consolidates multiple unspent transaction outputs into one or few destinations. "
            "Common causes include exchange wallet sweeps, mining pool payout aggregations, or pre-mixing structuring. "
            "High output fan-out dispatches funds from few inputs across numerous addresses, characteristic of exchange "
            "withdrawals, payroll distributions, or dusting attacks. These topological structures are distinct from peer transfers."
        ),
        "keywords": ["fan_in", "fan_out", "consolidation", "dispersion", "batching", "dusting"],
    },
    {
        "id": "kb_velocity_timing",
        "title": "Transaction Velocity and Fund Dwell Time",
        "content": (
            "Transaction velocity measures the frequency and dwell time of funds across addresses. "
            "Rapid parent-to-child spending (< 15 minutes) indicates automated pass-through or intermediate transit wallets. "
            "Bursts of correlated transactions in short rolling windows across shared address clusters often indicate "
            "structuring (smurfing) to avoid thresholds or rapid relay through automated gateways."
        ),
        "keywords": ["velocity", "rapid", "timing", "dwell", "burst", "structuring", "latency"],
    },
    {
        "id": "kb_fee_heuristics",
        "title": "Fee Rate Anomalies and Urgency Signals",
        "content": (
            "Mining fee rate (satoshis per virtual byte) reflects transaction urgency or automated bidding errors. "
            "Unusually high fee-to-value ratios (> 5% of transacted volume) or excessive fee rates (> 120 sat/vB) "
            "suggest high-urgency exfiltration or child-pays-for-parent (CPFP) acceleration. Sub-economic fees (< 1 sat/vB) "
            "frequently cause mempool eviction unless accelerated via Replace-By-Fee (RBF)."
        ),
        "keywords": ["fee", "rate", "sat_vb", "urgency", "ratio", "cpfp", "rbf"],
    },
    {
        "id": "kb_common_input",
        "title": "Common-Input Ownership Heuristic & Address Clustering",
        "content": (
            "The common-input ownership heuristic states that all inputs in a single multi-input transaction are "
            "controlled by the same entity, provided the transaction is not a collaborative CoinJoin. "
            "Address reuse across distinct transactions degrades pseudonymity and enables deterministic clustering."
        ),
        "keywords": ["common_input", "clustering", "reuse", "ownership", "coinjoin", "entity"],
    },
    {
        "id": "kb_aml_fatf_standards",
        "title": "FATF Red Flag Indicators for Virtual Assets",
        "content": (
            "FATF guidance identifies key behavioral red flags in virtual asset transactions: rapid movement of funds "
            "in and out of accounts, immediate transfer after receipt, structured values just below thresholds, "
            "transactions originating from or sent to multiple new addresses, and abnormal fee settings. "
            "Forensic analysts must treat these as risk indicators prompting inquiry, never as legal proof of criminality."
        ),
        "keywords": ["aml", "fatf", "red_flag", "risk", "investigation", "compliance", "behavioral"],
    },
]


class KnowledgeRetriever:
    """In-memory FAISS-backed semantic retriever for Bitcoin investigation heuristics."""

    def __init__(self):
        self.docs = BITCOIN_SECURITY_KNOWLEDGE
        self.dim = 64
        self.index = faiss.IndexFlatL2(self.dim)
        # Generate deterministic embeddings for each doc based on term hashing
        embeddings = [self._embed(d["title"] + " " + d["content"] + " " + " ".join(d["keywords"])) for d in self.docs]
        matrix = np.array(embeddings, dtype=np.float32)
        self.index.add(matrix)

    def _embed(self, text: str) -> list[float]:
        # Stable projection into 64-dimensional space
        vec = np.zeros(self.dim, dtype=np.float32)
        words = text.lower().replace(",", " ").replace(".", " ").replace("(", " ").replace(")", " ").split()
        for i, word in enumerate(words):
            h = hash(word) % self.dim
            vec[h] += 1.0 / (1.0 + np.log1p(i))
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec.tolist()

    def retrieve(self, query: str, top_k: int = 3) -> list[dict[str, str]]:
        q_vec = np.array([self._embed(query)], dtype=np.float32)
        distances, indices = self.index.search(q_vec, min(top_k, len(self.docs)))
        results = []
        for idx in indices[0]:
            if 0 <= idx < len(self.docs):
                results.append(self.docs[idx])
        return results


retriever = KnowledgeRetriever()


# --- LangGraph State Schema ---
class InvestigationState(TypedDict, total=False):
    case_id: str
    txid: str
    query: str
    transaction_facts: dict[str, Any]
    anomaly_evidence: dict[str, Any]
    graph_evidence: dict[str, Any]
    risk_factors: dict[str, Any]
    rag_context: list[dict[str, str]]
    investigation_report: dict[str, Any]
    execution_trace: list[str]


# --- Specialized Multi-Agent Nodes ---

def transaction_analysis_node(state: InvestigationState, db: Any) -> dict[str, Any]:
    """Agent 1: Transaction Analysis Agent — Retrieves verifiable transaction evidence."""
    txid = state["txid"]
    case_id = state["case_id"]
    t = db.transactions.find_one({"case_id": case_id, "txid": txid})

    if not t:
        return {
            "transaction_facts": {"error": f"Transaction {txid} not found in case database."},
            "execution_trace": state.get("execution_trace", []) + ["transaction_analysis:not_found"],
        }

    inputs = t.get("inputs", [])
    outputs = t.get("outputs", [])
    total_out = sum(o["value_sats"] for o in outputs)
    fee_sats = t.get("fee_sats")
    vsize = t.get("vsize") or 1
    fee_rate = round(fee_sats / vsize, 2) if fee_sats is not None and vsize else None

    facts = {
        "txid": txid,
        "input_count": len(inputs),
        "output_count": len(outputs),
        "total_output_sats": total_out,
        "total_output_btc": round(total_out / 1e8, 8),
        "fee_sats": fee_sats,
        "vsize": vsize,
        "fee_rate_sat_vb": fee_rate,
        "confirmed": t.get("confirmed", False),
        "confirmations": t.get("confirmations"),
        "observed_at": str(t.get("observed_at")) if t.get("observed_at") else None,
        "block_time": str(t.get("block_time")) if t.get("block_time") else None,
        "output_addresses": [o.get("address") for o in outputs if o.get("address")],
        "script_types": list({o.get("script_type") for o in outputs if o.get("script_type")}),
    }

    return {
        "transaction_facts": facts,
        "execution_trace": state.get("execution_trace", []) + ["transaction_analysis:completed"],
    }


def anomaly_analysis_node(state: InvestigationState, db: Any) -> dict[str, Any]:
    """Agent 2: Anomaly Analysis Agent — Evaluates Isolation Forest and feature vectors."""
    txid = state["txid"]
    case_id = state["case_id"]

    feature_doc = db.features.find_one({"case_id": case_id, "txid": txid})
    score = feature_doc.get("score", 0.0) if feature_doc else 0.0
    values = feature_doc.get("values", []) if feature_doc else []
    version = feature_doc.get("model_version", "unknown") if feature_doc else "not_scored"

    is_anomaly = score >= 97.0
    evidence = {
        "isolation_forest_percentile": score,
        "model_version": version,
        "is_statistical_outlier": is_anomaly,
        "feature_values": values,
        "interpretation": (
            f"Isolation Forest mid-rank percentile is {score:g}% (threshold: 97%). "
            + ("Flags statistical distribution divergence relative to case dataset." if is_anomaly else "Within normal baseline density.")
        ),
    }

    return {
        "anomaly_evidence": evidence,
        "execution_trace": state.get("execution_trace", []) + ["anomaly_analysis:completed"],
    }


def graph_investigation_node(state: InvestigationState, db: Any) -> dict[str, Any]:
    """Agent 3: Graph Investigation Agent — Explores connected addresses and UTXO lineages."""
    txid = state["txid"]
    case_id = state["case_id"]

    # In-degree / Parent connections
    t = db.transactions.find_one({"case_id": case_id, "txid": txid})
    parent_ids = list({i["prev_txid"] for i in t.get("inputs", [])} if t else set())
    parent_txs = list(db.transactions.find({"case_id": case_id, "txid": {"$in": parent_ids}}, {"txid": 1, "outputs": 1}))

    # Out-degree / Spenders
    spenders = list(db.transactions.find({"case_id": case_id, "inputs.prev_txid": txid}, {"txid": 1, "inputs": 1, "observed_at": 1}))
    child_txids = [s["txid"] for s in spenders]

    # Peeling chain check
    is_peel_hop = len(t.get("inputs", [])) == 1 and len(t.get("outputs", [])) == 2 if t else False
    connected_addrs = [o.get("address") for o in t.get("outputs", []) if o.get("address")] if t else []

    graph_facts = {
        "parent_transaction_count": len(parent_txs),
        "parent_txids": [p["txid"] for p in parent_txs],
        "child_spender_count": len(child_txids),
        "child_txids": child_txids[:10],
        "is_peel_candidate": is_peel_hop,
        "connected_addresses": connected_addrs[:10],
        "total_graph_degrees": len(parent_txs) + len(child_txids),
    }

    return {
        "graph_evidence": graph_facts,
        "execution_trace": state.get("execution_trace", []) + ["graph_investigation:completed"],
    }


def risk_assessment_node(state: InvestigationState, db: Any) -> dict[str, Any]:
    """Agent 4: Risk Assessment Agent — Summarizes deterministic risk rules and AML indicators."""
    txid = state["txid"]
    case_id = state["case_id"]

    alert = db.alerts.find_one({"case_id": case_id, "txid": txid})
    feature_doc = db.features.find_one({"case_id": case_id, "txid": txid})

    aml_indicators = alert.get("aml_indicators", []) if alert else (feature_doc.get("aml_indicators", []) if feature_doc else [])
    aml_score = alert.get("aml_risk_score", 0.0) if alert else (feature_doc.get("aml_risk_score", 0.0) if feature_doc else 0.0)
    rule_detections = alert.get("detections", []) if alert else []

    severity = alert.get("severity", "low") if alert else ("medium" if aml_score > 30 else "low")

    factors = {
        "severity": severity,
        "composite_aml_risk_score": aml_score,
        "active_aml_indicators": [
            {
                "code": ind.get("code"),
                "title": ind.get("title"),
                "observed": ind.get("observed"),
                "threshold": ind.get("threshold"),
                "unit": ind.get("unit"),
                "reason": ind.get("reason"),
            }
            for ind in aml_indicators
        ],
        "rule_detections_count": len(rule_detections),
        "is_flagged": alert is not None,
        "alert_title": alert.get("title") if alert else None,
        "disclaimer": "Behavioral indicators represent statistical or pattern triggers, not proof of illicit intent or crime.",
    }

    return {
        "risk_factors": factors,
        "execution_trace": state.get("execution_trace", []) + ["risk_assessment:completed"],
    }


def rag_knowledge_node(state: InvestigationState) -> dict[str, Any]:
    """Agent 5: RAG Knowledge Agent — Retrieves Bitcoin AML heuristics matching query and evidence."""
    query = state.get("query", "")
    risk_factors = state.get("risk_factors", {})
    active_codes = [ind["code"] for ind in risk_factors.get("active_aml_indicators", [])]

    search_text = f"{query} " + " ".join(active_codes)
    retrieved = retriever.retrieve(search_text, top_k=3)

    return {
        "rag_context": [
            {"id": doc["id"], "title": doc["title"], "content": doc["content"]}
            for doc in retrieved
        ],
        "execution_trace": state.get("execution_trace", []) + ["rag_knowledge:completed"],
    }


def ai_security_analyst_node(state: InvestigationState) -> dict[str, Any]:
    """Agent 6: AI Security Analyst Agent — Grounded Gemini synthesis or deterministic fallback."""
    tx_facts = state.get("transaction_facts", {})
    anomaly = state.get("anomaly_evidence", {})
    graph = state.get("graph_evidence", {})
    risk = state.get("risk_factors", {})
    rag = state.get("rag_context", [])
    query = state.get("query", "Analyze transaction risk and behavioral patterns.")

    # 1. Prepare deterministic structured sections (always guaranteed accurate)
    observed_evidence = [
        f"Transaction ID: {tx_facts.get('txid')}",
        f"Input Count: {tx_facts.get('input_count')} | Output Count: {tx_facts.get('output_count')}",
        f"Total Transacted: {tx_facts.get('total_output_sats', 0):,} satoshis ({tx_facts.get('total_output_btc', 0)} BTC)",
        f"Mining Fee: {tx_facts.get('fee_sats')} satoshis ({tx_facts.get('fee_rate_sat_vb')} sat/vB)",
        f"Confirmation Status: {'Confirmed' if tx_facts.get('confirmed') else 'Unconfirmed'} ({tx_facts.get('confirmations')} confirmations)",
        f"Direct Graph Connections: {graph.get('parent_transaction_count', 0)} parent input TXs, {graph.get('child_spender_count', 0)} child spender TXs",
    ]

    model_rule_indications = [
        f"Isolation Forest Anomaly Percentile: {anomaly.get('isolation_forest_percentile', 0)}%",
        f"Composite AML Risk Score: {risk.get('composite_aml_risk_score', 0)}/100 (Severity: {risk.get('severity', 'low').upper()})",
    ]
    for ind in risk.get("active_aml_indicators", []):
        model_rule_indications.append(
            f"Indicator [{ind.get('title')}]: Observed {ind.get('observed')} {ind.get('unit')} (Threshold: {ind.get('threshold')}). {ind.get('reason')}"
        )

    investigative_suggestions = [
        "Verify source of funds on parent input UTXOs using the Cytoscape graph explorer.",
        "Check address reuse across imported datasets to confirm counterparty clusters.",
        "If peeling chain behavior is indicated, trace downstream change outputs for terminal consolidation.",
        "Cross-reference mining fee spikes with prevailing mempool conditions at reported block time.",
    ]

    # 2. Check if Gemini API can enrich the grounded synthesis
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    narrative_explanation = ""

    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)

            prompt = f"""You are a professional Bitcoin Security and Blockchain Intelligence Analyst.
Investigator Query: {query}

VERIFIED TRANSACTION FACTS (Do not alter or add unobserved facts):
{json.dumps(tx_facts, indent=2)}

STATISTICAL ANOMALY EVIDENCE:
{json.dumps(anomaly, indent=2)}

GRAPH LINEAGE EVIDENCE:
{json.dumps(graph, indent=2)}

DETERMINISTIC RISK & AML INDICATORS:
{json.dumps(risk, indent=2)}

RAG BLOCKCHAIN KNOWLEDGE CONTEXT:
{json.dumps(rag, indent=2)}

INSTRUCTIONS:
Provide an auditable, objective analysis of this transaction.
STRICT GROUNDING RULES:
1. Ground every statement exclusively on the provided transaction facts, risk indicators, and RAG knowledge.
2. NEVER invent unobserved transactions, addresses, entities, or legal conclusions.
3. NEVER state that an indicator proves money laundering or criminal activity. Treat all findings as risk indicators requiring investigation.
4. Structure your response with a clear narrative summary, followed by specific takeaways.
"""
            # Using recommended gemini-3.8-flash model as per skill instructions
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
            )
            if response and response.text:
                narrative_explanation = response.text
        except Exception as err:
            logger.warning("Gemini AI Security Analyst fallback triggered: %s", err)
            narrative_explanation = (
                f"Automated deterministic summary: Transaction {tx_facts.get('txid', '')[:16]}... exhibits "
                f"a composite AML risk score of {risk.get('composite_aml_risk_score', 0)}/100 with "
                f"{len(risk.get('active_aml_indicators', []))} active behavioral indicators. "
                f"Isolation Forest mid-rank percentile is {anomaly.get('isolation_forest_percentile', 0)}%. "
                f"Review graph lineage for parent spenders and downstream output splits."
            )
    else:
        narrative_explanation = (
            f"Deterministic forensic analysis: Transaction {tx_facts.get('txid', '')[:16]}... evaluated against "
            f"case dataset baseline. Detected {len(risk.get('active_aml_indicators', []))} behavioral indicator triggers "
            f"yielding a composite risk score of {risk.get('composite_aml_risk_score', 0)}/100. "
            f"All findings represent objective statistical anomalies requiring human investigation."
        )

    report = {
        "status": "completed",
        "txid": tx_facts.get("txid"),
        "query": query,
        "narrative_explanation": narrative_explanation,
        "observed_evidence": observed_evidence,
        "model_rule_indications": model_rule_indications,
        "investigative_suggestions": investigative_suggestions,
        "contributing_indicators": risk.get("active_aml_indicators", []),
        "rag_sources": [r["title"] for r in rag],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "Grounding notice: Analysis is strictly synthesized from deterministic evidence and RAG knowledge. No unverified facts are assumed.",
    }

    return {
        "investigation_report": report,
        "execution_trace": state.get("execution_trace", []) + ["ai_security_analyst:completed"],
    }


# --- LangGraph Workflow Definition ---

def build_investigation_graph(db: Any):
    """Build and compile the LangGraph multi-agent investigation workflow."""
    workflow = StateGraph(InvestigationState)

    # Bind db to agent nodes
    workflow.add_node("transaction_analysis", lambda state: transaction_analysis_node(state, db))
    workflow.add_node("anomaly_analysis", lambda state: anomaly_analysis_node(state, db))
    workflow.add_node("graph_investigation", lambda state: graph_investigation_node(state, db))
    workflow.add_node("risk_assessment", lambda state: risk_assessment_node(state, db))
    workflow.add_node("rag_knowledge", rag_knowledge_node)
    workflow.add_node("ai_security_analyst", ai_security_analyst_node)

    # Sequential execution edges
    workflow.set_entry_point("transaction_analysis")
    workflow.add_edge("transaction_analysis", "anomaly_analysis")
    workflow.add_edge("anomaly_analysis", "graph_investigation")
    workflow.add_edge("graph_investigation", "risk_assessment")
    workflow.add_edge("risk_assessment", "rag_knowledge")
    workflow.add_edge("rag_knowledge", "ai_security_analyst")
    workflow.add_edge("ai_security_analyst", END)

    return workflow.compile()


def run_investigation(case_id: str, txid: str, query: str, db: Any) -> dict[str, Any]:
    """Execute the multi-agent investigation workflow for an investigator query."""
    try:
        app_graph = build_investigation_graph(db)
        initial_state: InvestigationState = {
            "case_id": case_id,
            "txid": txid,
            "query": query,
            "execution_trace": ["orchestrator:started"],
        }
        final_state = app_graph.invoke(initial_state)
        report = final_state.get("investigation_report", {})
        report["execution_trace"] = final_state.get("execution_trace", [])
        return report
    except Exception as exc:
        logger.exception("LangGraph workflow error: %s", exc)
        # Deterministic emergency fallback
        t = db.transactions.find_one({"case_id": case_id, "txid": txid}) or {}
        alert = db.alerts.find_one({"case_id": case_id, "txid": txid}) or {}
        return {
            "status": "completed_fallback",
            "txid": txid,
            "query": query,
            "narrative_explanation": f"Deterministic fallback report generated for transaction {txid}.",
            "observed_evidence": [
                f"Transaction ID: {txid}",
                f"Input Count: {len(t.get('inputs', []))} | Output Count: {len(t.get('outputs', []))}",
            ],
            "model_rule_indications": [
                f"Alert Status: {alert.get('severity', 'none').upper()}",
                f"Reason: {alert.get('title', 'No active alerts')}",
            ],
            "investigative_suggestions": [
                "Review Cytoscape graph connections directly.",
                "Inspect parent inputs and spending outputs.",
            ],
            "contributing_indicators": alert.get("aml_indicators", []),
            "rag_sources": ["Deterministic Rules & Schema Baseline"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": "Fallback mode: Deterministic facts presented directly.",
            "execution_trace": ["orchestrator:fallback"],
        }
