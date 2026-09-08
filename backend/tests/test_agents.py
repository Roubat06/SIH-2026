import pytest
from app.agents import retriever, run_investigation, build_investigation_graph
from app.analysis import training_data, parse, analyze
from app import db
import secrets


def test_rag_retriever_semantic_match():
    results = retriever.retrieve("peeling chain change address heuristic", top_k=2)
    assert len(results) >= 1
    assert any("peeling" in r["title"].lower() or "peeling" in r["content"].lower() for r in results)

    results_velocity = retriever.retrieve("transaction velocity burst rapid movement", top_k=2)
    assert any("velocity" in r["title"].lower() or "dwell" in r["content"].lower() for r in results_velocity)


def test_multi_agent_investigation_flow(client):
    from test_workflow import account, case
    account(client)
    cid = case(client)
    # Post demo transactions
    r = client.post(f"/api/cases/{cid}/demo")
    assert r.status_code == 202
    from app.worker import tick
    tick()

    # Get an alert to investigate
    alerts = client.get(f"/api/cases/{cid}/alerts").json()
    assert len(alerts) > 0
    target_txid = alerts[0]["txid"]

    # Call /investigate endpoint
    resp = client.post(
        f"/api/cases/{cid}/investigate",
        json={"txid": target_txid, "query": "Assess peeling chain and high volume risk."},
    )
    assert resp.status_code == 200, resp.text
    report = resp.json()

    assert report["txid"] == target_txid
    assert "observed_evidence" in report and len(report["observed_evidence"]) > 0
    assert "model_rule_indications" in report and len(report["model_rule_indications"]) > 0
    assert "investigative_suggestions" in report and len(report["investigative_suggestions"]) > 0
    assert "rag_sources" in report and len(report["rag_sources"]) > 0
    assert "execution_trace" in report
    # Ensure all agents executed in trace
    trace = report["execution_trace"]
    assert any("transaction_analysis" in t for t in trace)
    assert any("anomaly_analysis" in t for t in trace)
    assert any("graph_investigation" in t for t in trace)
    assert any("risk_assessment" in t for t in trace)
    assert any("rag_knowledge" in t for t in trace)
    assert any("ai_security_analyst" in t for t in trace)
