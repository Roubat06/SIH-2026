from fastapi import APIRouter, Depends
from ...schemas.models import RAGSearchRequest, RAGSearchResponse
from ...utils.security import get_current_user
from ...rag.store import search_security_knowledge

router = APIRouter(prefix='/api/rag', tags=['Security Knowledge Base'])

@router.post('/search')
def query_knowledge_base(req: RAGSearchRequest, user: dict = Depends(get_current_user)):
    results = search_security_knowledge(req.query, top_k=req.limit)
    return {'results': results, 'total_matches': len(results)}
