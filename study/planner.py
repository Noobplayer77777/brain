from dataclasses import dataclass
from typing import List, Optional
import pandas as pd
from datetime import datetime
from core.db import get_connection
from questions.analytics import high_yield

@dataclass
class Task:
    task_type: str # 'learn', 'review', 'drill_pyq', 'redo_mistake', 'mock'
    concept_id: Optional[str]
    title: str
    reason: str
    est_minutes: int
    question_id: Optional[str] = None

def get_exam_date(subject: str) -> Optional[datetime]:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (f"exam_date_{subject}",)).fetchone()
        if row and row['value']:
            try:
                return datetime.fromisoformat(row['value'])
            except:
                pass
    return None

def plan_today(subject: str, minutes_available: int = 90) -> List[Task]:
    tasks = []
    minutes_planned = 0
    
    with get_connection() as conn:
        # 1. Mistakes to Redo (highest priority)
        mistakes = conn.execute("""
            SELECT m.attempt_id, m.concept_id, c.name, q.id as q_id, q.text 
            FROM mistakes m
            JOIN concepts c ON m.concept_id = c.id
            JOIN attempts a ON m.attempt_id = a.id
            JOIN questions q ON a.question_id = q.id
            WHERE c.subject = ? AND m.note != 'redone'
            LIMIT 5
        """, (subject,)).fetchall()
        
        for m in mistakes:
            if minutes_planned + 10 > minutes_available: break
            tasks.append(Task(
                task_type="redo_mistake",
                concept_id=m['concept_id'],
                question_id=m['q_id'],
                title=f"Redo Mistake: {m['name']}",
                reason="Address past mistake to improve mastery",
                est_minutes=10
            ))
            minutes_planned += 10
            
        # 2. Reviews Due Today
        reviews = conn.execute("""
            SELECT c.id, c.name, m.score
            FROM mastery m
            JOIN concepts c ON m.concept_id = c.id
            WHERE c.subject = ? AND m.next_review <= CURRENT_TIMESTAMP
            ORDER BY m.next_review ASC
            LIMIT 10
        """, (subject,)).fetchall()
        
        for r in reviews:
            if minutes_planned + 5 > minutes_available: break
            tasks.append(Task(
                task_type="review",
                concept_id=r['id'],
                title=f"Review: {r['name']}",
                reason="Spaced repetition scheduled for today",
                est_minutes=5
            ))
            minutes_planned += 5
            
        # 3. Learn / Drill weak high-yield concepts
        if minutes_planned < minutes_available:
            yields = high_yield(subject)
            y_dict = {y['id']: y['score'] for y in yields}
            
            # Get prerequisites graph
            prereqs_raw = conn.execute("SELECT concept_id, prereq_concept_id FROM prerequisites").fetchall()
            prereq_map = {}
            for p in prereqs_raw:
                if p['concept_id'] not in prereq_map: prereq_map[p['concept_id']] = []
                prereq_map[p['concept_id']].append(p['prereq_concept_id'])
                
            # Get all concepts and mastery
            all_concepts = conn.execute("SELECT id, name FROM concepts WHERE subject = ?", (subject,)).fetchall()
            mastery_dict = {}
            mastery_raw = conn.execute("SELECT concept_id, score FROM mastery").fetchall()
            for m in mastery_raw: mastery_dict[m['concept_id']] = m['score']
            
            # Score concepts for learning
            learn_candidates = []
            for c in all_concepts:
                cid = c['id']
                m_score = mastery_dict.get(cid, 0.0)
                if m_score > 0.8: continue # Mastered
                
                y_score = y_dict.get(cid, 1.0)
                centrality = sum(1 for k, v in prereq_map.items() if cid in v)
                
                priority = (1.0 - m_score) * y_score * (1 + centrality)
                learn_candidates.append((priority, cid, c['name']))
                
            learn_candidates.sort(reverse=True, key=lambda x: x[0])
            
            for score, cid, name in learn_candidates:
                if minutes_planned + 15 > minutes_available: break
                
                # Check prereqs
                my_prereqs = prereq_map.get(cid, [])
                unmet = [p for p in my_prereqs if mastery_dict.get(p, 0.0) < 0.5]
                
                if unmet:
                    # Enqueue the first unmet prereq instead
                    unmet_id = unmet[0]
                    unmet_name = conn.execute("SELECT name FROM concepts WHERE id=?", (unmet_id,)).fetchone()['name']
                    tasks.append(Task(
                        task_type="learn", concept_id=unmet_id, title=f"Learn Prerequisite: {unmet_name}",
                        reason=f"Required before learning {name}", est_minutes=15
                    ))
                else:
                    task_type = "drill_pyq" if mastery_dict.get(cid, 0.0) > 0.4 else "learn"
                    tasks.append(Task(
                        task_type=task_type, concept_id=cid, title=f"Focus: {name}",
                        reason="Weak + High-Yield topic", est_minutes=15
                    ))
                minutes_planned += 15

    return tasks
