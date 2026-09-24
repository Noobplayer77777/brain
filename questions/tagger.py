import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import argparse
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from core.db import get_connection
from core.ollama_client import generate, embed
from core.retrieval import keyword_search
from rich.console import Console
from rich.progress import track

console = Console()

class ConceptTag(BaseModel):
    concept_id: str
    confidence: float

class QuestionTagging(BaseModel):
    concept_tags: List[ConceptTag]
    archetype: Literal["Define X", "Compare X and Y", "Derive Z", "Design a schema for...", "Solve numerical", "Prove theorem", "Apply process", "Other"]
    inferred_difficulty: int = Field(ge=1, le=5)

def run_tagging(subject: str, resume: bool = False):
    with get_connection() as conn:
        if not resume:
            conn.execute("DELETE FROM question_concepts WHERE question_id IN (SELECT id FROM questions WHERE subject = ?)", (subject,))
            
        questions = conn.execute("""
            SELECT id, text, marks, question_type, archetype FROM questions 
            WHERE subject = ?
        """, (subject,)).fetchall()
        
        # Load concepts for prompt injection
        concepts = conn.execute("SELECT id, name, definition FROM concepts WHERE subject = ?", (subject,)).fetchall()
        
    if not questions:
        console.print(f"[yellow]No questions found for {subject}. Run parser first.[/yellow]")
        return
        
    if not concepts:
        console.print(f"[yellow]No concepts found for {subject}. Run concept extractor first.[/yellow]")
        return
        
    schema = QuestionTagging.model_json_schema()
    sys_prompt = f"""You are an AI exam analyzer.
Tag the given question with the MOST relevant concept IDs from the provided list.
Also classify the question into an archetype and infer its difficulty (1-5).
Return strict JSON matching this schema:
{json.dumps(schema)}
"""

    for q in track(questions, description="Tagging questions..."):
        if resume and q['archetype']:
            # Assume already tagged if archetype is set
            continue
            
        # Optional: pre-filter concepts using embeddings or keyword search to save LLM context
        # For small concept lists, we just pass them all
        concept_list_str = "\n".join([f"ID: {c['id']} | Name: {c['name']} | Def: {c['definition']}" for c in concepts])
        
        prompt = f"Concepts Available:\n{concept_list_str}\n\nQuestion: {q['text']}\nMarks: {q['marks']}\nType: {q['question_type']}"
        
        try:
            resp = generate(prompt, system=sys_prompt, json_mode=True)
            data = json.loads(resp)
            result = QuestionTagging.model_validate(data)
            
            with get_connection() as conn:
                conn.execute("UPDATE questions SET archetype = ?, difficulty = ? WHERE id = ?", (result.archetype, result.inferred_difficulty, q['id']))
                
                for tag in result.concept_tags:
                    # Verify ID exists
                    exists = any(c['id'] == tag.concept_id for c in concepts)
                    if exists:
                        conn.execute("""
                            INSERT OR REPLACE INTO question_concepts (question_id, concept_id, confidence)
                            VALUES (?, ?, ?)
                        """, (q['id'], tag.concept_id, tag.confidence))
        except Exception as e:
            console.print(f"[red]Failed tagging for question {q['id']}: {e}[/red]")
            
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM question_concepts qc JOIN questions q ON qc.question_id = q.id WHERE q.subject = ?", (subject,)).fetchone()[0]
        console.print(f"[green]Tagging complete. Total tags: {count}[/green]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    
    run_tagging(args.subject, args.resume)
