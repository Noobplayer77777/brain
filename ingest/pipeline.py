import os
import argparse
import hashlib
import uuid
import chromadb
from pathlib import Path
from rich.console import Console
from rich.progress import track, Progress
from rich.table import Table

from core.db import get_connection, init_db
from core.ollama_client import embed
from config import CHROMA_DIR, CHUNK_SIZE, CHUNK_OVERLAP
from ingest.pdf import parse_pdf
from ingest.pptx import parse_pptx
from ingest.docx import parse_docx
from ingest.txt_md import parse_txt
from ingest.chunker import generate_chunks

console = Console()

def get_file_hash(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def ingest_file(path: Path, subject: str, collection) -> dict:
    file_hash = get_file_hash(str(path))
    ext = path.suffix.lower()
    
    with get_connection() as conn:
        existing = conn.execute("SELECT id, status FROM resources WHERE sha256 = ?", (file_hash,)).fetchone()
        if existing and existing['status'] == 'done':
            return {"status": "skipped", "reason": "Already ingested"}
            
    resource_id = str(uuid.uuid4())
    if existing:
        resource_id = existing['id']
        with get_connection() as conn:
            conn.execute("UPDATE resources SET status = 'processing', subject = ? WHERE id = ?", (subject, resource_id))
    else:
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO resources (id, path, filename, filetype, subject, sha256, status)
                VALUES (?, ?, ?, ?, ?, ?, 'processing')
            """, (resource_id, str(path), path.name, ext, subject, file_hash))
    
    try:
        if ext == '.pdf': parsed_data = parse_pdf(str(path))
        elif ext == '.pptx': parsed_data = parse_pptx(str(path))
        elif ext == '.docx': parsed_data = parse_docx(str(path))
        elif ext in ['.txt', '.md']: parsed_data = parse_txt(str(path))
        else: raise ValueError(f"Unsupported extension {ext}")
        
        chunks = generate_chunks(parsed_data, resource_id, CHUNK_SIZE, CHUNK_OVERLAP)
        
        # SQLite insertion
        with get_connection() as conn:
            conn.execute("DELETE FROM chunks WHERE resource_id = ?", (resource_id,))
            for c in chunks:
                conn.execute("""
                    INSERT INTO chunks (chunk_id, resource_id, chunk_index, text, page_start, page_end, slide_no, token_count, char_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (c["chunk_id"], c["resource_id"], c["chunk_index"], c["text"], 
                      c["page_start"], c["page_end"], c["slide_no"], c["token_count"], c["char_count"]))
                
            conn.execute("UPDATE resources SET num_pages = ?, status = 'done' WHERE id = ?", (len(parsed_data), resource_id))
        
        # Embeddings in batches of 16
        batch_size = 16
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            texts = [c["text"] for c in batch]
            embeddings = embed(texts)
            
            ids = [c["chunk_id"] for c in batch]
            metadatas = [
                {
                    "resource_id": c["resource_id"],
                    "subject": subject,
                    "filename": path.name,
                    "page": str(c["page_start"]) if c["page_start"] else "",
                    "slide": str(c["slide_no"]) if c["slide_no"] else "",
                } for c in batch
            ]
            collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=texts)
            
        return {"status": "done", "chunks": len(chunks)}
        
    except Exception as e:
        with get_connection() as conn:
            conn.execute("UPDATE resources SET status = 'failed', error_msg = ? WHERE id = ?", (str(e), resource_id))
        return {"status": "failed", "reason": str(e)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", required=True)
    parser.add_argument("--path", required=True)
    args = parser.parse_args()
    
    init_db()
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = chroma_client.get_or_create_collection(name="exam_brain")
    
    target_path = Path(args.path)
    if not target_path.exists():
        console.print(f"[red]Path {target_path} does not exist.[/red]")
        return
        
    files = []
    if target_path.is_file():
        files.append(target_path)
    else:
        for ext in ['.pdf', '.pptx', '.docx', '.txt', '.md']:
            files.extend(target_path.rglob(f"*{ext}"))
            
    table = Table(title="Ingestion Summary")
    table.add_column("File", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Chunks", justify="right")
    table.add_column("Notes", style="yellow")
    
    with Progress() as progress:
        task = progress.add_task("[cyan]Ingesting files...", total=len(files))
        
        for f in files:
            res = ingest_file(f, args.subject, collection)
            if res["status"] == "done":
                table.add_row(f.name, "[green]Done", str(res["chunks"]), "")
            elif res["status"] == "skipped":
                table.add_row(f.name, "[blue]Skipped", "-", res["reason"])
            else:
                table.add_row(f.name, "[red]Failed", "-", res["reason"])
                
            progress.advance(task)
            
    console.print(table)

if __name__ == "__main__":
    main()
