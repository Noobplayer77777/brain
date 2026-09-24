import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import uuid
import pandas as pd
from datetime import datetime, timedelta
from rich.console import Console
from core.db import get_connection
from study.quiz import generate_quiz
from study.grading import grade_answer
from study.mastery import update_mastery

console = Console()

def run_simulation(subject: str = "DBMS"):
    console.print(f"Generating 10-question quiz for {subject} (mode=pyq)...")
    questions = generate_quiz(subject, 10, mode="pyq")
    
    # In my dummy data, I only have 4 PYQ questions for DBMS.
    # The quiz generator will return 4. That's fine.
    
    for i, q in enumerate(questions):
        console.print(f"\n[bold blue]Question {i+1}: {q['text']}[/bold blue]")
        
        # Simulate an answer (some good, some bad)
        if "1NF" in q['text'] or "First Normal Form" in q['text']:
            # good answer
            user_ans = "First Normal Form requires that all attributes contain only atomic values. No repeating groups are allowed."
        else:
            # bad answer
            user_ans = "I don't remember this. Something about diagrams."
            
        console.print(f"User Answer: {user_ans}")
        
        res = grade_answer(q['text'], q['marks'], user_ans, subject, q.get('model_answer'))
        console.print(f"[green]Grading Result:[/green]")
        console.print(f"Score: {res.score}/{res.max_score}")
        console.print(f"Feedback: {res.feedback}")
        console.print(f"Missing Points: {res.missing_points}")
        console.print(f"Error Types: {res.error_types}")
        
        attempt_id = str(uuid.uuid4())
        
        with get_connection() as conn:
            c_row = conn.execute("SELECT concept_id FROM question_concepts WHERE question_id = ?", (q['id'],)).fetchone()
            c_id = c_row['concept_id'] if c_row else None
            
            conn.execute("""
                INSERT INTO attempts (id, question_id, user_answer, score, max_score, graded_by, feedback)
                VALUES (?, ?, ?, ?, ?, 'llm', ?)
            """, (attempt_id, q['id'], user_ans, res.score, res.max_score, res.feedback))
            
            if c_id and "none" not in res.error_types:
                for err in res.error_types:
                    conn.execute("""
                        INSERT INTO mistakes (id, attempt_id, concept_id, error_type, note)
                        VALUES (hex(randomblob(16)), ?, ?, ?, ?)
                    """, (attempt_id, c_id, err, res.feedback))
                    
        # Call this OUTSIDE the connection block to prevent SQLite database is locked error
        if c_id:
            update_mastery(c_id, res.score / res.max_score, res.error_types)
                        
    console.print("\n[bold]Mastery Table Snapshot:[/bold]")
    with get_connection() as conn:
        df = pd.read_sql("""
            SELECT c.name, m.score, m.attempts_count, m.next_review, m.interval_days, m.ease
            FROM mastery m JOIN concepts c ON m.concept_id = c.id
        """, conn)
        console.print(df)
        
if __name__ == "__main__":
    run_simulation("DBMS")
