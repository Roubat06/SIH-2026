"""
Embeds the typology knowledge base + past alert explanations into a
MongoDB collection with a vector index, so the n8n Precedent/Typology
agents can do retrieval without standing up separate vector-DB infra.

Works with MongoDB Atlas Vector Search. If you're self-hosting Mongo
without Atlas, swap `precedents.create_search_index(...)` for a local
alternative (e.g. Qdrant, or a brute-force cosine scan for demo scale —
a hackathon dataset is small enough that brute force is fine).

Usage:
    pip install pymongo sentence-transformers  # offline-capable embedder
    export MONGO_URI="mongodb://127.0.0.1:27017"
    export MONGO_DB="bitcoin_sentinel"
    python ingest_embeddings.py
"""

import os
import re
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer

MONGO_URI = os.environ["MONGO_URI"]
MONGO_DB = os.environ.get("MONGO_DB", "bitcoin_sentinel")
TYPOLOGY_KB_PATH = os.path.join(os.path.dirname(__file__), "typology_kb.md")

# Local, offline-capable embedding model — keeps the "runs without
# internet once dependencies are present" property the project already
# has for everything else. Swap for an OpenAI/Voyage embedder if you'd
# rather trade that off for quality.
model = SentenceTransformer("all-MiniLM-L6-v2")


def chunk_markdown_by_h2(text: str) -> list[dict]:
    """Split the typology KB into one chunk per `## ` section."""
    sections = re.split(r"\n(?=## )", text)
    chunks = []
    for s in sections:
        s = s.strip()
        if not s.startswith("## "):
            continue
        title = s.splitlines()[0].replace("## ", "").strip()
        chunks.append({"title": title, "text": s})
    return chunks


def ingest_typology_kb(db):
    coll = db["rag_typology_chunks"]
    coll.delete_many({"source": "typology_kb"})
    with open(TYPOLOGY_KB_PATH, "r") as f:
        raw = f.read()
    chunks = chunk_markdown_by_h2(raw)
    docs = []
    for chunk in chunks:
        embedding = model.encode(chunk["text"]).tolist()
        docs.append({
            "source": "typology_kb",
            "title": chunk["title"],
            "text": chunk["text"],
            "embedding": embedding,
        })
    if docs:
        coll.insert_many(docs)
    print(f"Ingested {len(docs)} typology chunks.")


def ingest_reviewed_alert_precedents(db):
    """Embed past alerts that already have an analyst review/explanation
    so future alerts can retrieve 'this looks like a case we've already
    reviewed' precedent, not just abstract typologies."""
    alerts_coll = db["alerts"]
    precedent_coll = db["rag_alert_precedents"]
    precedent_coll.delete_many({})

    cursor = alerts_coll.find({"review_status": {"$in": ["reviewed", "dismissed"]}})
    docs = []
    for alert in cursor:
        narrative = alert.get("explanation") or alert.get("reason") or ""
        analyst_note = alert.get("analyst_note", "")
        text = f"{narrative}\nAnalyst note: {analyst_note}".strip()
        if not text:
            continue
        embedding = model.encode(text).tolist()
        docs.append({
            "case_id": alert.get("case_id"),
            "alert_id": alert.get("_id"),
            "review_status": alert.get("review_status"),
            "text": text,
            "embedding": embedding,
        })
    if docs:
        precedent_coll.insert_many(docs)
    print(f"Ingested {len(docs)} reviewed-alert precedents.")


def ensure_vector_index_hint():
    print(
        "\nReminder: create an Atlas Vector Search index on "
        "'rag_typology_chunks.embedding' and 'rag_alert_precedents.embedding' "
        "(384 dims, cosine similarity) via the Atlas UI or "
        "db.collection.createSearchIndex(...). For self-hosted Mongo without "
        "Atlas, query-time brute-force cosine similarity is fine at hackathon "
        "scale — see the MCP server's search_similar_alerts tool."
    )


if __name__ == "__main__":
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    ingest_typology_kb(db)
    ingest_reviewed_alert_precedents(db)
    ensure_vector_index_hint()
