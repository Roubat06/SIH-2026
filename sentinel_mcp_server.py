"""
Sentinel MCP Server
--------------------
Exposes the existing Sentinel Tool FastAPI backend as MCP tools so any
MCP-aware client (Claude, an n8n AI Agent node, etc.) can query case
data without new auth machinery.

Auth: the Sentinel backend uses opaque, server-revocable HttpOnly
session cookies (see repo README). This server holds one such cookie
(from a service/analyst account you provision) and forwards it on every
call. Rotate it the same way you'd rotate any analyst session.

All tools here are READ-ONLY against case data. Writing an analyst note
back is intentionally left to the n8n workflow's own HTTP Request node,
not to this server, so an agent can never mutate a case purely by
calling a tool.

Run:
    pip install "mcp[cli]" httpx
    export SENTINEL_BASE_URL="http://127.0.0.1:8000"
    export SENTINEL_SESSION_COOKIE="session=<value>"
    python sentinel_mcp_server.py
"""

import os
import httpx
import numpy as np
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
from mcp.server.fastmcp import FastMCP

BASE_URL = os.environ.get("SENTINEL_BASE_URL", "http://127.0.0.1:8000")
SESSION_COOKIE = os.environ.get("SENTINEL_SESSION_COOKIE", "")
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://127.0.0.1:27017")
MONGO_DB = os.environ.get("MONGO_DB", "bitcoin_sentinel")

mcp = FastMCP("sentinel-tool")
_embed_model = None  # lazy-loaded, only needed by the two RAG tools below


def _embedder() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embed_model


def _cosine_topk(query_vec: np.ndarray, docs: list[dict], k: int) -> list[dict]:
    if not docs:
        return []
    mat = np.array([d["embedding"] for d in docs])
    sims = mat @ query_vec / (np.linalg.norm(mat, axis=1) * np.linalg.norm(query_vec) + 1e-9)
    top_idx = np.argsort(-sims)[:k]
    return [{**{kk: vv for kk, vv in docs[i].items() if kk != "embedding"},
             "similarity": float(sims[i])} for i in top_idx]


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=BASE_URL,
        headers={"Cookie": SESSION_COOKIE, "Accept": "application/json"},
        timeout=15.0,
    )


@mcp.tool()
def get_case_alerts(case_id: str, priority: str | None = None,
                     review_status: str | None = None, limit: int = 20) -> dict:
    """List alerts for a case, optionally filtered by priority
    (high/medium/low) or review_status (open/reviewed/dismissed).
    Returns raw alert records including detection evidence."""
    params = {"limit": limit}
    if priority:
        params["priority"] = priority
    if review_status:
        params["review_status"] = review_status
    with _client() as c:
        r = c.get(f"/api/cases/{case_id}/alerts", params=params)
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_alert_detail(case_id: str, alert_id: str) -> dict:
    """Fetch one alert's full detection evidence: triggering stage,
    detector, observed value, threshold, comparison operator, baseline,
    and reason. Includes both rule and model signals if both fired."""
    with _client() as c:
        r = c.get(f"/api/cases/{case_id}/alerts/{alert_id}")
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_transaction(case_id: str, txid: str) -> dict:
    """Fetch the rich transaction record: chain metadata, confirmation
    snapshot, both timestamps, fees, resolved inputs, observed spending
    links, script info, associated anomalies, and source lineage."""
    with _client() as c:
        r = c.get(f"/api/cases/{case_id}/transactions/{txid}")
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_investigation_timeline(case_id: str, event_type: str | None = None,
                                date_from: str | None = None,
                                date_to: str | None = None,
                                limit: int = 50) -> dict:
    """Fetch the case timeline: transaction observations, block times,
    network observations, pipeline events, detection events, and
    analyst actions. Dates are UTC ISO-8601 strings."""
    params = {"limit": limit}
    if event_type:
        params["event_type"] = event_type
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to
    with _client() as c:
        r = c.get(f"/api/cases/{case_id}/timeline", params=params)
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_transaction_graph(case_id: str, txid: str, hops: int = 2) -> dict:
    """Fetch the bounded transaction graph (server caps at ~25 nodes /
    2 hops) centered on a transaction. Shows blockchain output
    relationships only — not wallet-ownership or identity clustering."""
    with _client() as c:
        r = c.get(f"/api/cases/{case_id}/graph", params={"txid": txid, "hops": hops})
        r.raise_for_status()
        return r.json()


@mcp.tool()
def match_typology(alert_summary: str, top_k: int = 3) -> list[dict]:
    """RAG lookup: given a plain-text description of an alert's shape
    and evidence (e.g. 'input count 42, largest output share 0.91,
    chain of 6 linked transactions each peeling a small remainder'),
    return the top-k matching known laundering typologies from the
    knowledge base, each with its similarity score and caveat text.
    This is retrieval only — the calling agent must still phrase any
    match as 'resembles', never as a determination."""
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    docs = list(db["rag_typology_chunks"].find({}, {"_id": 0}))
    query_vec = _embedder().encode(alert_summary)
    return _cosine_topk(query_vec, docs, top_k)


@mcp.tool()
def search_similar_precedents(alert_summary: str, case_id: str | None = None,
                               top_k: int = 3) -> list[dict]:
    """RAG lookup over previously reviewed/dismissed alerts. Returns
    the most similar past alerts (by narrative + analyst note text)
    so the current alert can be framed against precedent an analyst
    has already judged. Optionally scope to one case_id."""
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    query = {"case_id": case_id} if case_id else {}
    docs = list(db["rag_alert_precedents"].find(query, {"_id": 0}))
    query_vec = _embedder().encode(alert_summary)
    return _cosine_topk(query_vec, docs, top_k)


if __name__ == "__main__":
    mcp.run(transport="stdio")
