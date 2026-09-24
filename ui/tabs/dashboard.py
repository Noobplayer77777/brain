import streamlit as st
import pandas as pd
from datetime import datetime
from core.db import get_connection

def render():
    st.header("📊 Exam Brain Dashboard")
    
    with get_connection() as conn:
        subjects = [r['name'] for r in conn.execute("SELECT name FROM subjects").fetchall()]
        if not subjects:
            st.info("No subjects found. Please run Phase 0/1 setup.")
            return
            
        subject = st.selectbox("Dashboard Subject", subjects, key="dash_subj")
        
        # Top Metrics
        concepts_total = conn.execute("SELECT COUNT(*) FROM concepts WHERE subject = ?", (subject,)).fetchone()[0]
        concepts_mastered = conn.execute("""
            SELECT COUNT(*) FROM mastery m 
            JOIN concepts c ON m.concept_id = c.id 
            WHERE c.subject = ? AND m.score > 0.8
        """, (subject,)).fetchone()[0]
        
        reviews_due = conn.execute("""
            SELECT COUNT(*) FROM mastery m
            JOIN concepts c ON m.concept_id = c.id
            WHERE c.subject = ? AND m.next_review <= CURRENT_TIMESTAMP
        """, (subject,)).fetchone()[0]
        
        exam_date_row = conn.execute("SELECT value FROM settings WHERE key = ?", (f"exam_date_{subject}",)).fetchone()
        days_to_exam = "Set in Settings"
        if exam_date_row and exam_date_row['value']:
            try:
                ed = datetime.fromisoformat(exam_date_row['value'])
                days_to_exam = (ed - datetime.now()).days
            except: pass
            
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Concepts Mastered", f"{concepts_mastered} / {concepts_total}")
        col2.metric("Reviews Due Today", reviews_due)
        col3.metric("Days to Exam", days_to_exam)
        
        # Mocks
        mocks = conn.execute("SELECT COUNT(*), AVG(total_score/max_score) FROM mock_exams WHERE subject = ?", (subject,)).fetchone()
        avg_mock = f"{mocks[1]*100:.1f}%" if mocks[1] else "N/A"
        col4.metric("Avg Mock Score", avg_mock, f"{mocks[0]} taken")
        
        st.divider()
        
        # Top Weakest High-Yield
        st.subheader("⚠️ Weakest High-Yield Concepts")
        weak = pd.read_sql("""
            SELECT c.name, m.score as mastery, 
                   (SELECT COUNT(*) FROM question_concepts qc WHERE qc.concept_id = c.id) as pyq_freq
            FROM concepts c
            LEFT JOIN mastery m ON c.id = m.concept_id
            WHERE c.subject = ? AND (m.score IS NULL OR m.score < 0.6)
            ORDER BY pyq_freq DESC LIMIT 5
        """, conn, params=(subject,))
        
        if not weak.empty:
            st.dataframe(weak, use_container_width=True)
        else:
            st.success("You have no highly-tested weak concepts!")
            
        st.divider()
        st.subheader("📈 Mastery Trend")
        trend = pd.read_sql("""
            SELECT DATE(reviewed_at) as date, AVG(mastery_after) as avg_mastery
            FROM review_log rl
            JOIN concepts c ON rl.concept_id = c.id
            WHERE c.subject = ?
            GROUP BY DATE(reviewed_at)
            ORDER BY date ASC
        """, conn, params=(subject,))
        
        if not trend.empty:
            st.line_chart(trend.set_index('date'))
        else:
            st.info("Take quizzes to generate a mastery trend line.")
