import streamlit as st
from datetime import datetime, timedelta
import uuid
from study.planner import plan_today
from core.db import get_connection

def render():
    st.header("📅 Daily Study Plan")
    
    subject = st.selectbox("Subject to Plan", ["DBMS", "DMGT", "Compiler Design", "Cloud Architecture Design"], key="plan_subj")
    minutes = st.slider("Minutes Available Today", 15, 240, 90, step=15)
    
    if st.button("Generate Plan"):
        st.session_state.today_plan = plan_today(subject, minutes)
        
    if 'today_plan' in st.session_state and st.session_state.today_plan:
        st.subheader("Your Plan")
        for i, t in enumerate(st.session_state.today_plan):
            with st.expander(f"Task {i+1}: {t.title} ({t.est_minutes} min)"):
                st.write(f"**Type:** {t.task_type}")
                st.write(f"**Why:** {t.reason}")
                
                if st.button(f"Start Session", key=f"start_{i}"):
                    session_id = str(uuid.uuid4())
                    with get_connection() as conn:
                        conn.execute("""
                            INSERT INTO study_sessions (id, task_type, concept_id, question_id, minutes)
                            VALUES (?, ?, ?, ?, ?)
                        """, (session_id, t.task_type, t.concept_id, t.question_id, t.est_minutes))
                    st.success("Session logged! Go to Practice tab to execute.")
                    
        st.divider()
        st.subheader("Weekly Outlook")
        # simple 7 day view based on spaced repetition due dates
        with get_connection() as conn:
            due_counts = conn.execute("""
                SELECT DATE(next_review) as dt, COUNT(*) as cnt
                FROM mastery m JOIN concepts c ON m.concept_id = c.id
                WHERE c.subject = ? AND next_review <= datetime('now', '+7 days')
                GROUP BY dt ORDER BY dt ASC
            """, (subject,)).fetchall()
            
        for d in due_counts:
            st.write(f"- **{d['dt']}**: {d['cnt']} concepts to review")
