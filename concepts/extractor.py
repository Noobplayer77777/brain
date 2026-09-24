import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import uuid
import math
import argparse
from pydantic import BaseModel, Field
from typing import List, Literal
from core.db import get_connection
from core.retrieval import hybrid_search
from core.ollama_client import generate, embed
from syllabus.tree import flatten_topics
from rich.console import Console

console = Console()

class ConceptModel(BaseModel):
    name: str
    type: Literal["definition", "formula", "theorem", "process", "comparison", "algorithm", "diagram", "example"]
    definition: str
    difficulty: int = Field(ge=1, le=5)

class ConceptExtraction(BaseModel):
    concepts: List[ConceptModel]

def cosine_similarity(v1, v2):
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0: return 0.0
    return dot / (norm1 * norm2)

def extract_concepts_for_topic(topic: dict, subject: str) -> List[ConceptModel]:
    query = f"{topic['topic_title']}"
    hits = hybrid_search(query, subject=subject, k=5)
    
    if not hits:
        return []
        
    context = "\n\n".join([f"--- Chunk ---\n{h.text}" for h in hits])
    
    schema = ConceptExtraction.model_json_schema()
    sys_prompt = f"""You are an expert educator. Identify atomic concepts from the provided chunks relevant to the topic: '{topic['topic_title']}'.
Return a JSON object matching this schema exactly:
{json.dumps(schema)}
Do not include preamble. Ensure the concepts are granular and specific.
"""
    prompt = f"Topic: {topic['topic_title']}\n\nContext:\n{context}"
    
    for attempt in range(2):
        try:
            resp = generate(prompt, system=sys_prompt, json_mode=True)
            data = json.loads(resp)
            return ConceptExtraction.model_validate(data).concepts
        except Exception as e:
            if attempt == 1:
                console.print(f"[red]Failed to extract concepts for {topic['topic_title']}[/red]")
                return []
            prompt += f"\n\nPrevious failure: {e}. Return strict JSON."
    return []

def run_extraction(subject: str):
    topics = flatten_topics(subject)
    if not topics:
        console.print(f"[yellow]No topics found for {subject}. Load syllabus first.[/yellow]")
        return
        
    console.print(f"Running extraction for {len(topics)} topics in {subject}...")
    
    # Preload existing concepts
    existing_concepts = []
    with get_connection() as conn:
        rows = conn.execute("SELECT id, canonical_name FROM concepts WHERE subject = ?", (subject,)).fetchall()
        if rows:
            names = [r['canonical_name'] for r in rows]
            embeddings = embed(names)
            for r, e in zip(rows, embeddings):
                existing_concepts.append({"id": r['id'], "name": r['canonical_name'], "emb": e})
                
    for topic in topics:
        console.print(f"Extracting for topic: {topic['topic_title']}")
        extracted = extract_concepts_for_topic(topic, subject)
        
        if not extracted: continue
        
        # We'll batch embed the new names to compare
        new_names = [c.name.lower().strip() for c in extracted]
        new_embs = embed(new_names)
        
        with get_connection() as conn:
            for c_mod, emb in zip(extracted, new_embs):
                c_name = c_mod.name
                c_canon = c_name.lower().strip()
                
                # Check for duplicates
                best_match = None
                best_score = 0.0
                for ec in existing_concepts:
                    score = cosine_similarity(emb, ec["emb"])
                    if score > best_score:
                        best_score = score
                        best_match = ec
                        
                if best_score > 0.90 and best_match:
                    concept_id = best_match["id"]
                else:
                    concept_id = str(uuid.uuid4())
                    conn.execute("""
                        INSERT INTO concepts (id, subject, name, canonical_name, type, definition, difficulty)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (concept_id, subject, c_name, c_canon, c_mod.type, c_mod.definition, c_mod.difficulty))
                    existing_concepts.append({"id": concept_id, "name": c_canon, "emb": emb})
                    
                # Link to topic
                conn.execute("""
                    INSERT OR IGNORE INTO concept_links (concept_id, topic_id, weight)
                    VALUES (?, ?, 1.0)
                """, (concept_id, topic['topic_id']))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", required=True)
    args = parser.parse_args()
    
    run_extraction(args.subject)
    
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM concepts WHERE subject = ?", (args.subject,)).fetchone()[0]
        console.print(f"[green]Extraction complete. Total concepts for {args.subject}: {count}[/green]")
