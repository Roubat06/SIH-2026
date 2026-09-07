# Sentinel Tool — AI Agent Layer (MCP + RAG + n8n multi-agent)

This adds an **advisory AI layer** on top of the existing Sentinel Tool
(React + FastAPI + MongoDB, Isolation Forest `sentinel-iforest-v2` + rule
engine). It does **not** replace or touch the deterministic detection
pipeline — it consumes its output and makes it easier for a human analyst
to act on.

## Current ML (unchanged)

| Stage | Method | Notes |
|---|---|---|
| Rule detection | Hand-coded thresholds | e.g. ≥10 inputs/outputs → fan-out/fan-in flag |
| Model scoring | Isolation Forest, `sentinel-iforest-v2` | 100 estimators, seed 42, 5 features, requires ≥40 records/case, in-dataset percentile only |

Nothing below changes those numbers or claims better precision/recall —
per the repo's own scope notes, that would need real reference-baseline
evaluation first.

## What gets added

```
                         ┌─────────────────────────┐
                         │   Sentinel FastAPI       │
                         │  (alerts, tx, timeline)  │
                         └────────────┬─────────────┘
                                      │ REST (session cookie)
                         ┌────────────▼─────────────┐
                         │   Sentinel MCP Server     │  ← new
                         │ tools: get_alert,         │
                         │ get_tx, get_timeline,     │
                         │ search_precedents,        │
                         │ match_typology            │
                         └────────────┬─────────────┘
                                      │ MCP (stdio/SSE)
        ┌────────────────────────────┼─────────────────────────────┐
        │                     n8n multi-agent workflow              │
        │  Webhook (new alert) → 4 agents, each an n8n AI Agent     │
        │  node with the MCP tools attached:                        │
        │                                                            │
        │  1. Triage Agent        — pulls alert + evidence,          │
        │                            restates it factually           │
        │  2. Precedent Agent     — RAG search over past reviewed    │
        │                            alerts + typology KB            │
        │  3. Typology Agent      — matches known laundering         │
        │                            patterns, cites which features  │
        │                            triggered the match             │
        │  4. Analyst Brief Agent — composes the final advisory       │
        │                            note, always labelled AI-       │
        │                            generated / non-authoritative   │
        │                                                            │
        │  → HTTP Request node posts the brief back to               │
        │    /cases/{id}/alerts/{id}/notes (or your notes endpoint)  │
        └────────────────────────────────────────────────────────────┘
                                      │
                         ┌────────────▼─────────────┐
                         │  Mongo Atlas Vector Search │  ← new (reuses
                         │  or local vector index     │    existing Mongo,
                         │  over: past alert           │    no new infra)
                         │  explanations + typology KB │
                         └───────────────────────────┘
```

## The "unique" piece: Typology-Aware Explainable Narrator

Most hackathon teams stop at "ML flags anomaly → show score." The gap in
almost every anomaly-detection tool (including this one, by its own
scope notes) is that a percentile score doesn't tell an analyst **why**,
or whether it matches a **known pattern** a human would recognize
(peel chain, layering through a mixer cluster, structuring below a
reporting threshold, etc.).

`rag/typology_kb.md` is a small seed knowledge base of these patterns,
written as retrievable documents. The **Typology Agent** does retrieval
against it and against previously-reviewed alerts in the same case (or
workspace, if you allow cross-case precedent later), then reports:

- which specific typology(ies) the alert resembles
- which exact feature values / rule matches support that
- how confident that match is — and explicitly not a probability of crime

This turns a black-box percentile into a cited, checkable narrative,
which is both a strong demo moment and consistent with the project's own
"exploratory, not calibrated" stance — the agent layer never claims more
certainty than the underlying model gives it.

## Guardrails baked in (don't skip these)

- Every agent output is stored as a **note attached to the alert**, never
  as a new alert or an overwrite of model/rule fields.
- The Analyst Brief Agent's system prompt requires it to (a) quote actual
  feature values from the evidence record, (b) say "resembles" not "is",
  and (c) end with "AI-generated, for analyst review" every time.
- MCP tools are **read-only** against the Sentinel API except the final
  "post note" call, which n8n makes directly (not via MCP), so no agent
  can silently mutate case data through tool use.
- Viewer-role accounts should not trigger the workflow — gate the webhook
  on the analyst/owner role, matching the existing case-permission model.

## Files in this scaffold

- `mcp-server/sentinel_mcp_server.py` — MCP server exposing read tools
  over the existing FastAPI backend.
- `rag/typology_kb.md` — seed typology knowledge base (the unique bit).
- `rag/ingest_embeddings.py` — embeds typology KB + past alert
  explanations into a Mongo collection for vector search.
- `n8n/sentinel_multi_agent_workflow.json` — importable n8n workflow
  with the 4 agents wired to the MCP tools.

## What you'll need to fill in

1. Map the tool functions in `sentinel_mcp_server.py` to your actual
   route paths (I used the field/endpoint names implied by the README —
   confirm against `backend/app/main.py`'s route list).
2. Point `MONGO_URI` in `ingest_embeddings.py` at the same MongoDB the
   app uses, and pick an embedding model (OpenAI, or a local
   sentence-transformers model if you want to stay offline-capable,
   matching the project's "runs without internet after build" ethos).
3. In n8n, set credentials for whichever LLM you use for the agent
   nodes, and set the MCP Client Tool node's connection to point at
   wherever you run `sentinel_mcp_server.py` (stdio if n8n and the
   server are on the same host, SSE if remote).
