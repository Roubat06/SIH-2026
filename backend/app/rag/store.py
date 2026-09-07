from typing import List, Dict, Any
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
