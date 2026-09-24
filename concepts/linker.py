import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import argparse
from pydantic import BaseModel, Field
from typing import List, Literal
from core.db import get_connection
from core.retrieval import hybrid_search
from core.ollama_client import generate
from rich.console import Console
from rich.progress import track

console = Console()

class ConceptResourceLink(BaseModel):
    chunk_id: str
    relation: Literal["explains", "mentions", "assesses", "exemplifies", "none"]
    confidence: float

class ConceptLinkingModel(BaseModel):
    links: List[ConceptResourceLink]

def run_linking(subject: str, resume: bool = False):
    with get_connection() as conn:
        if not resume:
            conn.execute("DELETE FROM concept_resources WHERE concept_id IN (SELECT id FROM concepts WHERE subject = ?)", (subject,))
            
        concepts = conn.execute("""
            SELECT id, name, definition FROM concepts 
            WHERE subject = ?
        """, (subject,)).fetchall()
        
    if not concepts:
        console.print(f"[yellow]No concepts found for {subject}. Run extractor first.[/yellow]")
        return
        
    console.print(f"Linking {len(concepts)} concepts to resources...")
    
    schema = ConceptLinkingModel.model_json_schema()
    sys_prompt = f"""You are an educational AI. Classify the relationship between a concept and multiple text chunks.
Relations allowed: "explains", "mentions", "assesses", "exemplifies", "none".
Return strict JSON matching this schema:
{json.dumps(schema)}
Only include chunks that actually have a relationship.
"""

    for concept in track(concepts, description="Linking concepts..."):
        # Check if already processed
        if resume:
            with get_connection() as conn:
                existing = conn.execute("SELECT COUNT(*) FROM concept_resources WHERE concept_id = ?", (concept['id'],)).fetchone()[0]
                if existing > 0:
                    continue
                    
        query = f"{concept['name']} {concept['definition']}"
        hits = hybrid_search(query, subject=subject, k=10)
        
        if not hits: continue
        
        context = ""
        for h in hits:
            context += f"--- Chunk ID: {h.chunk_id} ---\n{h.text}\n\n"
            
        prompt = f"Concept: {concept['name']}\nDefinition: {concept['definition']}\n\nChunks to evaluate:\n{context}"
        
        try:
            resp = generate(prompt, system=sys_prompt, json_mode=True)
            data = json.loads(resp)
            links = ConceptLinkingModel.model_validate(data).links
            
            with get_connection() as conn:
                for link in links:
                    if link.relation == "none": continue
                    
                    # Find resource_id for this chunk
                    res_row = conn.execute("SELECT resource_id FROM chunks WHERE chunk_id = ?", (link.chunk_id,)).fetchone()
                    if not res_row: continue
                    
                    conn.execute("""
                        INSERT OR REPLACE INTO concept_resources (concept_id, resource_id, chunk_id, relation, confidence)
                        VALUES (?, ?, ?, ?, ?)
                    """, (concept['id'], res_row['resource_id'], link.chunk_id, link.relation, link.confidence))
                    
        except Exception as e:
            console.print(f"[red]Failed linking for concept {concept['name']}: {e}[/red]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    
    run_linking(args.subject, args.resume)
    
    with get_connection() as conn:
        count = conn.execute("""
            SELECT COUNT(*) FROM concept_resources cr
            JOIN concepts c ON cr.concept_id = c.id
            WHERE c.subject = ?
        """, (args.subject,)).fetchone()[0]
        console.print(f"[green]Linking complete. Total concept-resource edges: {count}[/green]")
