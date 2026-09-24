import pandas as pd
from core.db import get_connection

def get_coverage_matrix(subject: str) -> pd.DataFrame:
    query = """
    SELECT 
        c.id as concept_id,
        c.name as concept_name,
        c.type,
        c.difficulty,
        (SELECT GROUP_CONCAT(t.title, ', ') FROM concept_links cl JOIN topics t ON cl.topic_id = t.id WHERE cl.concept_id = c.id) as topics,
        COUNT(DISTINCT cr.resource_id) as num_resources,
        SUM(CASE WHEN cr.relation = 'explains' THEN 1 ELSE 0 END) as explaining_chunks,
        SUM(CASE WHEN cr.relation = 'mentions' THEN 1 ELSE 0 END) as mentioning_chunks,
        SUM(CASE WHEN cr.relation = 'assesses' THEN 1 ELSE 0 END) as num_questions
    FROM concepts c
    LEFT JOIN concept_resources cr ON c.id = cr.concept_id
    WHERE c.subject = ?
    GROUP BY c.id
    """
    
    with get_connection() as conn:
        df = pd.read_sql(query, conn, params=(subject,))
        
    if df.empty:
        return pd.DataFrame()
        
    def determine_status(row):
        if row['num_resources'] == 0: return 'blind'
        if row['explaining_chunks'] > 0: return 'covered'
        if row['mentioning_chunks'] > 0: return 'thin'
        return 'thin'
        
    df['status'] = df.apply(determine_status, axis=1)
    
    # Flag untested if 0 questions
    df['untested'] = df['num_questions'] == 0
    
    return df
