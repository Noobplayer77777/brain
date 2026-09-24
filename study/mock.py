import json
import uuid
import pandas as pd
from datetime import datetime
from core.db import get_connection
from study.quiz import generate_quiz
from study.grading import grade_answer
from study.mastery import update_mastery
from questions.analytics import question_archetypes

def generate_mock(subject: str, total_marks: int = 50) -> list:
    # Get archetypes distribution
    archs = question_archetypes(subject)
    
    questions = []
    marks_accumulated = 0
    
    with get_connection() as conn:
        if archs:
            # Try to build matching distribution from PYQs
            for arch in archs:
                if marks_accumulated >= total_marks: break
                q_row = conn.execute("SELECT * FROM questions WHERE subject = ? AND archetype = ? ORDER BY RANDOM() LIMIT 1", (subject, arch['archetype'])).fetchone()
                if q_row:
                    questions.append(dict(q_row))
                    marks_accumulated += q_row['marks']
                    
        # Fill remaining with random questions
        while marks_accumulated < total_marks:
            q_row = conn.execute("SELECT * FROM questions WHERE subject = ? ORDER BY RANDOM() LIMIT 1", (subject,)).fetchone()
            if not q_row: break
            # Ensure no duplicates
            if not any(q['id'] == q_row['id'] for q in questions):
                questions.append(dict(q_row))
                marks_accumulated += q_row['marks']
            else:
                break # Avoid infinite loop if dataset is too small
                
    return questions

def submit_mock(subject: str, mock_responses: list, duration_min: int):
    mock_id = str(uuid.uuid4())
    total_score = 0.0
    max_score = 0.0
    report = []
    
    # Grade everything in memory first to avoid holding DB lock
    for resp in mock_responses:
        q = resp['question']
        ans = resp['user_answer']
        grading = grade_answer(q['text'], q['marks'], ans, subject, q.get('model_answer'))
        total_score += grading.score
        max_score += q['marks']
        
        report.append({
            "question_id": q['id'],
            "question_text": q['text'],
            "user_answer": ans,
            "score": grading.score,
            "max_score": q['marks'],
            "feedback": grading.feedback,
            "error_types": grading.error_types,
            "missing_points": grading.missing_points
        })
        
    # Write to DB
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO mock_exams (id, subject, duration_min, total_score, max_score, report_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (mock_id, subject, duration_min, total_score, max_score, json.dumps(report)))
        
        for r in report:
            c_row = conn.execute("SELECT concept_id FROM question_concepts WHERE question_id = ?", (r['question_id'],)).fetchone()
            c_id = c_row['concept_id'] if c_row else None
            
            attempt_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO attempts (id, question_id, user_answer, score, max_score, graded_by, feedback, missing_points)
                VALUES (?, ?, ?, ?, ?, 'llm', ?, ?)
            """, (attempt_id, r['question_id'], r['user_answer'], r['score'], r['max_score'], r['feedback'], json.dumps(r['missing_points'])))
            
            if c_id:
                # Can't call update_mastery here because it opens a connection. 
                # We will just do a quick inline EWMA update since it's a mock.
                # In real code we'd refactor update_mastery to take a cursor.
                pass
                
    # Update masteries OUTSIDE the main connection
    for r in report:
        with get_connection() as conn:
            c_row = conn.execute("SELECT concept_id FROM question_concepts WHERE question_id = ?", (r['question_id'],)).fetchone()
            c_id = c_row['concept_id'] if c_row else None
        if c_id:
            update_mastery(c_id, r['score'] / r['max_score'], r['error_types'])
            
    return mock_id, total_score, max_score, report
