import pandas as pd
from core.db import get_connection
from core.ollama_client import embed
import numpy as np

def cosine_similarity(v1, v2):
    dot = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0: return 0.0
    return dot / (norm1 * norm2)

def high_yield(subject: str) -> list:
    query = """
    SELECT 
        c.id, c.name, 
        COUNT(qc.question_id) as freq, 
        AVG(q.marks) as avg_marks,
        MAX(q.year) as latest_year
    FROM concepts c
    JOIN question_concepts qc ON c.id = qc.concept_id
    JOIN questions q ON qc.question_id = q.id
    WHERE c.subject = ?
    GROUP BY c.id
    """
    with get_connection() as conn:
        df = pd.read_sql(query, conn, params=(subject,))
        
    if df.empty: return []
    
    # Recency weight: 1.0 for latest, decreases slightly
    max_yr = df['latest_year'].max()
    df['recency_weight'] = df['latest_year'].apply(lambda y: 1.0 - (max_yr - y)*0.1 if (max_yr - y) < 5 else 0.5)
    
    df['score'] = df['freq'] * df['avg_marks'] * df['recency_weight']
    df = df.sort_values('score', ascending=False)
    
    return df.to_dict('records')

def question_archetypes(subject: str) -> list:
    query = """
    SELECT archetype, COUNT(*) as count
    FROM questions
    WHERE subject = ? AND archetype IS NOT NULL
    GROUP BY archetype
    ORDER BY count DESC
    """
    with get_connection() as conn:
        df = pd.read_sql(query, conn, params=(subject,))
    return df.to_dict('records')

def repeat_questions(subject: str) -> list:
    with get_connection() as conn:
        questions = conn.execute("SELECT id, text, year, marks FROM questions WHERE subject = ?", (subject,)).fetchall()
        
    if len(questions) < 2: return []
    
    texts = [q['text'] for q in questions]
    embs = embed(texts)
    
    repeats = []
    visited = set()
    
    for i in range(len(questions)):
        if i in visited: continue
        cluster = [dict(questions[i])]
        visited.add(i)
        
        for j in range(i+1, len(questions)):
            if j in visited: continue
            
            sim = cosine_similarity(embs[i], embs[j])
            if sim > 0.85:
                cluster.append(dict(questions[j]))
                visited.add(j)
                
        if len(cluster) > 1:
            repeats.append(cluster)
            
    return repeats

def untested_concepts(subject: str) -> list:
    query = """
    SELECT id, name, definition
    FROM concepts
    WHERE subject = ? AND id NOT IN (SELECT concept_id FROM question_concepts)
    """
    with get_connection() as conn:
        df = pd.read_sql(query, conn, params=(subject,))
    return df.to_dict('records')
