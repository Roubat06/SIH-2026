import math
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
