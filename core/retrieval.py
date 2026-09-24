import re
from dataclasses import dataclass
from typing import List, Optional
import chromadb
from core.db import get_connection
from core.ollama_client import embed, generate
from config import CHROMA_DIR, LLM_MODEL

@dataclass
class Hit:
    chunk_id: str
    resource_id: str
    filename: str
    subject: str
    page: str
    slide: str
    text: str
    score: float

chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

def embed_query(text: str) -> list[float]:
    return embed([text])[0]

def vector_search(query: str, subject: Optional[str] = None, k: int = 20) -> List[Hit]:
    collection = chroma_client.get_or_create_collection(name="exam_brain")
    emb = embed_query(query)
    
    where = {"subject": subject} if subject and subject != "All" else None
    
    try:
        results = collection.query(query_embeddings=[emb], n_results=k, where=where, include=["metadatas", "documents", "distances"])
    except Exception:
        return []
        
    hits = []
    if not results["ids"] or not results["ids"][0]:
        return hits
        
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i] or {}
        doc = results["documents"][0][i]
        dist = results["distances"][0][i] # smaller is better (L2 distance)
        
        hits.append(Hit(
            chunk_id=results["ids"][0][i],
            resource_id=meta.get("resource_id", ""),
            filename=meta.get("filename", ""),
            subject=meta.get("subject", ""),
            page=meta.get("page", ""),
            slide=meta.get("slide", ""),
            text=doc,
            score=1.0 / (1.0 + dist)
        ))
    return hits

def keyword_search(query: str, subject: Optional[str] = None, k: int = 20) -> List[Hit]:
    words = re.findall(r'\w+', query)
    if not words:
        return []
    match_clause = " OR ".join(words)
    
    hits = []
    with get_connection() as conn:
        if subject and subject != "All":
            sql = """
                SELECT c.chunk_id, c.resource_id, r.filename, r.subject, c.page_start, c.slide_no, c.text, bm25(chunks_fts) as bm25_score
                FROM chunks_fts f
                JOIN chunks c ON f.rowid = c.id
                JOIN resources r ON c.resource_id = r.id
                WHERE chunks_fts MATCH ? AND r.subject = ?
                ORDER BY bm25_score ASC LIMIT ?
            """
            rows = conn.execute(sql, (match_clause, subject, k)).fetchall()
        else:
            sql = """
                SELECT c.chunk_id, c.resource_id, r.filename, r.subject, c.page_start, c.slide_no, c.text, bm25(chunks_fts) as bm25_score
                FROM chunks_fts f
                JOIN chunks c ON f.rowid = c.id
                JOIN resources r ON c.resource_id = r.id
                WHERE chunks_fts MATCH ?
                ORDER BY bm25_score ASC LIMIT ?
            """
            rows = conn.execute(sql, (match_clause, k)).fetchall()
            
        for r in rows:
            hits.append(Hit(
                chunk_id=r['chunk_id'],
                resource_id=r['resource_id'],
                filename=r['filename'],
                subject=r['subject'],
                page=str(r['page_start']) if r['page_start'] else "",
                slide=str(r['slide_no']) if r['slide_no'] else "",
                text=r['text'],
                score=abs(r['bm25_score'])
            ))
    return hits

def hybrid_search(query: str, subject: Optional[str] = None, k: int = 8) -> List[Hit]:
    v_hits = vector_search(query, subject, k=20)
    k_hits = keyword_search(query, subject, k=20)
    
    rrf_k = 60
    scores = {}
    hit_map = {}
    
    for rank, hit in enumerate(v_hits):
        scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (rrf_k + rank + 1)
        hit_map[hit.chunk_id] = hit
        
    for rank, hit in enumerate(k_hits):
        scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (rrf_k + rank + 1)
        if hit.chunk_id not in hit_map:
            hit_map[hit.chunk_id] = hit
            
    sorted_chunks = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    final_hits = []
    for chunk_id, score in sorted_chunks[:k]:
        h = hit_map[chunk_id]
        h.score = score
        final_hits.append(h)
        
    return final_hits

def expand_query(query: str) -> str:
    sys_prompt = "You are a search query expansion assistant. Paraphrase the user's query into 2-3 alternative phrasings to improve retrieval. Return ONLY the new keywords/phrases separated by spaces, no preamble."
    try:
        expanded = generate(query, system=sys_prompt)
        return f"{query} {expanded}"
    except Exception:
        return query
