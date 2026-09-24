from datetime import datetime, timedelta
from core.db import get_connection
import pandas as pd

def init_mastery_if_missing(concept_id: str):
    with get_connection() as conn:
        existing = conn.execute("SELECT concept_id FROM mastery WHERE concept_id = ?", (concept_id,)).fetchone()
        if not existing:
            conn.execute("""
                INSERT INTO mastery (concept_id, score, confidence, attempts_count, correct_count, next_review, interval_days, ease)
                VALUES (?, 0.0, 0.0, 0, 0, ?, 0.0, 2.5)
            """, (concept_id, datetime.now()))

def update_mastery(concept_id: str, attempt_score_ratio: float, error_types: list):
    init_mastery_if_missing(concept_id)
    
    # Compute SM-2 Quality (0-5)
    # Penalize heavily for conceptual/factual errors
    penalty = 0
    if "conceptual" in error_types or "factual" in error_types:
        penalty = 2
        
    if attempt_score_ratio >= 0.8:
        q = 5 - penalty
    elif attempt_score_ratio >= 0.6:
        q = 4 - penalty
    elif attempt_score_ratio >= 0.4:
        q = 3 - penalty
    else:
        q = 2 - penalty
        
    q = max(0, q) # floor at 0
    
    with get_connection() as conn:
        m = conn.execute("SELECT * FROM mastery WHERE concept_id = ?", (concept_id,)).fetchone()
        
        attempts = m['attempts_count'] + 1
        corrects = m['correct_count'] + (1 if attempt_score_ratio >= 0.8 else 0)
        ease = m['ease']
        interval = m['interval_days']
        old_score = m['score']
        
        # Calculate new ease
        ease = ease + 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)
        ease = max(1.3, ease)
        
        # Calculate interval
        if q < 3:
            interval = 1.0
        else:
            if attempts == 1:
                interval = 1.0
            elif attempts == 2:
                interval = 6.0
            else:
                interval = interval * ease
                
        next_rev = datetime.now() + timedelta(days=interval)
        
        # Exponential moving average for raw score
        new_score = (0.3 * attempt_score_ratio) + (0.7 * old_score)
        
        conn.execute("""
            UPDATE mastery 
            SET score = ?, attempts_count = ?, correct_count = ?, 
                last_reviewed = ?, next_review = ?, interval_days = ?, ease = ?
            WHERE concept_id = ?
        """, (new_score, attempts, corrects, datetime.now(), next_rev, interval, ease, concept_id))
        
        # Log it
        conn.execute("""
            INSERT INTO review_log (id, concept_id, quality, mastery_before, mastery_after)
            VALUES (hex(randomblob(16)), ?, ?, ?, ?)
        """, (concept_id, q, old_score, new_score))

def get_due_reviews(subject: str) -> pd.DataFrame:
    query = """
    SELECT c.name, m.score, m.next_review, m.interval_days, m.attempts_count
    FROM mastery m
    JOIN concepts c ON m.concept_id = c.id
    WHERE c.subject = ? AND m.next_review <= CURRENT_TIMESTAMP
    ORDER BY m.next_review ASC
    """
    with get_connection() as conn:
        return pd.read_sql(query, conn)
