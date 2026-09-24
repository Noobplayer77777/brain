import chromadb
from rich.console import Console
from core.db import get_connection
from core.ollama_client import embed
from config import CHROMA_DIR

console = Console()

def reindex():
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        chroma_client.delete_collection("exam_brain")
    except Exception:
        pass
    collection = chroma_client.create_collection("exam_brain")
    
    with get_connection() as conn:
        chunks = conn.execute("""
            SELECT c.chunk_id, c.text, c.resource_id, c.page_start, c.slide_no, r.subject, r.filename
            FROM chunks c
            JOIN resources r ON c.resource_id = r.id
        """).fetchall()
        
        conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
        
    if not chunks:
        console.print("No chunks to reindex.")
        return
        
    batch_size = 16
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        texts = [c['text'] for c in batch]
        embeddings = embed(texts)
        
        ids = [c['chunk_id'] for c in batch]
        metadatas = [
            {
                "resource_id": c["resource_id"],
                "subject": c["subject"],
                "filename": c["filename"],
                "page": str(c["page_start"]) if c["page_start"] else "",
                "slide": str(c["slide_no"]) if c["slide_no"] else "",
            } for c in batch
        ]
        collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=texts)
        console.print(f"Reindexed batch {i//batch_size + 1}")
        
    console.print("[green]Reindexing complete![/green]")

if __name__ == "__main__":
    reindex()
