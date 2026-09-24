import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import uuid
import argparse
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from core.db import get_connection, init_db
from core.ollama_client import generate
from ingest.pdf import parse_pdf
from rich.console import Console

console = Console()

class QuestionSubModel(BaseModel):
    question_number: str
    text: str
    marks: int
    question_type: Literal["mcq", "short", "long", "numerical", "derivation", "proof", "design", "case_study"]

class QuestionModel(BaseModel):
    question_number: str
    text: str
    marks: int
    question_type: Literal["mcq", "short", "long", "numerical", "derivation", "proof", "design", "case_study"]
    sub_questions: List[QuestionSubModel] = Field(default_factory=list)

class PaperExtraction(BaseModel):
    questions: List[QuestionModel]

def parse_paper(text: str) -> List[QuestionModel]:
    schema = PaperExtraction.model_json_schema()
    sys_prompt = f"""You are an expert exam paper parser. Extract all individual questions from the raw text.
Strip out headers, footers, and general instructions.
Return a strict JSON object matching this schema:
{json.dumps(schema)}
Ensure nested sub-questions are grouped under their parent if applicable, or treat them as separate questions if they stand alone. Do not add any preamble.
"""
    prompt = f"Raw Exam Text:\n{text}"
    
    for attempt in range(2):
        try:
            resp = generate(prompt, system=sys_prompt, json_mode=True)
            data = json.loads(resp)
            return PaperExtraction.model_validate(data).questions
        except Exception as e:
            if attempt == 1:
                console.print(f"[red]Failed parsing paper after 2 attempts: {e}[/red]")
                return []
            prompt += f"\n\nPrevious failure: {e}. Return strict JSON."
    return []

def run_ingest(subject: str, path: str, year: int, exam_type: str, source_type: str = "pyq", model_answer_path: str = None):
    target = Path(path)
    if not target.exists():
        console.print(f"[red]File {path} not found.[/red]")
        return
        
    pages = parse_pdf(str(target))
    raw_text = "\n".join([p.get('text', '') for p in pages])
    
    model_answer_text = None
    if model_answer_path and Path(model_answer_path).exists():
        ans_pages = parse_pdf(model_answer_path)
        model_answer_text = "\n".join([p.get('text', '') for p in ans_pages])
        
    console.print(f"Parsing {target.name} with LLM...")
    questions = parse_paper(raw_text)
    
    if not questions:
        console.print("[yellow]No questions extracted.[/yellow]")
        return
        
    with get_connection() as conn:
        for q in questions:
            q_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO questions (id, subject, source_type, source_name, year, exam_type, question_number, text, marks, question_type, model_answer)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (q_id, subject, source_type, target.name, year, exam_type, q.question_number, q.text, q.marks, q.question_type, model_answer_text))
            
            for sq in q.sub_questions:
                sq_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO questions (id, subject, source_type, source_name, year, exam_type, question_number, text, marks, question_type, model_answer)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (sq_id, subject, source_type, target.name, year, exam_type, f"{q.question_number}.{sq.question_number}", sq.text, sq.marks, sq.question_type, model_answer_text))
                
    total = len(questions) + sum(len(q.sub_questions) for q in questions)
    console.print(f"[green]Successfully parsed and inserted {total} questions from {target.name}[/green]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", required=True)
    parser.add_argument("--path", required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--exam-type", required=True)
    parser.add_argument("--source-type", default="pyq")
    parser.add_argument("--model-answer", default=None)
    
    args = parser.parse_args()
    init_db()
    run_ingest(args.subject, args.path, args.year, args.exam_type, args.source_type, args.model_answer)
