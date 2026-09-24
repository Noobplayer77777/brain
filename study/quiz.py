import uuid
import json
import random
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from core.db import get_connection
from core.ollama_client import generate
from core.retrieval import vector_search
from rich.console import Console

console = Console()

class GeneratedQuestion(BaseModel):
    text: str
    marks: int
    question_type: Literal["mcq", "short", "long", "numerical"]
    model_answer: str
    source_chunk_id: str

class QuizGenerationResponse(BaseModel):
    questions: List[GeneratedQuestion]

def get_pyq_questions(subject: str, n: int) -> list:
    with get_connection() as conn:
        questions = conn.execute("""
            SELECT id, text, marks, question_type, model_answer 
            FROM questions 
            WHERE subject = ? 
            ORDER BY RANDOM() LIMIT ?
        """, (subject, n)).fetchall()
        return [dict(q) for q in questions]

def generate_questions(subject: str, n: int) -> list:
    """Generate novel questions grounded in retrieved chunks."""
    # Retrieve some random chunks
    # We will pick a random topic from the subject
    with get_connection() as conn:
        topics = conn.execute("SELECT title FROM topics JOIN modules m ON module_id = m.id WHERE m.subject = ? ORDER BY RANDOM() LIMIT 1", (subject,)).fetchall()
        
    if not topics:
        return []
        
    query = topics[0]['title']
    hits = vector_search(query, subject=subject, k=3)
    if not hits: return []
    
    context = ""
    for h in hits:
        context += f"--- Chunk {h.chunk_id} ---\n{h.text}\n\n"
        
    schema = QuizGenerationResponse.model_json_schema()
    sys_prompt = f"""You are an exam generator. Create {n} novel questions based strictly on the provided chunks.
Return strict JSON matching this schema:
{json.dumps(schema)}
Every question MUST cite the source_chunk_id it was derived from. Do not hallucinate external knowledge.
"""

    prompt = f"Context:\n{context}"
    
    try:
        resp = generate(prompt, system=sys_prompt, json_mode=True)
        data = json.loads(resp)
        generated = QuizGenerationResponse.model_validate(data).questions
        
        # Format to match PYQ schema structure roughly
        out = []
        for g in generated:
            out.append({
                "id": str(uuid.uuid4()),  # Temporary ID for the session
                "text": g.text,
                "marks": g.marks,
                "question_type": g.question_type,
                "model_answer": g.model_answer,
                "source_chunk_id": g.source_chunk_id,
                "is_generated": True
            })
        return out
    except Exception as e:
        console.print(f"[red]Generation failed: {e}[/red]")
        return []

def generate_quiz(subject: str, n: int = 10, mode: str = "pyq") -> list:
    if mode == "pyq":
        return get_pyq_questions(subject, n)
    elif mode == "generated":
        return generate_questions(subject, n)
    else: # mixed
        half = n // 2
        return get_pyq_questions(subject, half) + generate_questions(subject, n - half)
