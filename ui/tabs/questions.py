import streamlit as st
import pandas as pd
from core.db import get_connection
from questions.analytics import high_yield, question_archetypes, repeat_questions, untested_concepts

def render():
    st.header("📝 Questions & PYQs")
    
    subject_filter = st.selectbox("Select Subject", ["DBMS", "DMGT", "Compiler Design", "Cloud Architecture Design"], key="q_subj")
    
    tab1, tab2, tab3 = st.tabs(["Browse", "🎯 Exam Radar", "🔁 Repeats"])
    
    with tab1:
        st.subheader("Question Bank")
        with get_connection() as conn:
            df = pd.read_sql("""
                SELECT q.id, q.year, q.exam_type, q.marks, q.question_type, q.text, q.archetype
                FROM questions q
                WHERE q.subject = ?
                ORDER BY q.year DESC
            """, conn, params=(subject_filter,))
            
        if df.empty:
            st.info("No questions loaded.")
        else:
            st.dataframe(df[['year', 'exam_type', 'marks', 'question_type', 'text', 'archetype']], use_container_width=True)
            
            st.divider()
            st.subheader("Question Details")
            q_id = st.selectbox("Inspect Question", df['id'].tolist(), format_func=lambda x: df[df['id']==x]['text'].values[0][:80] + "...")
            
            if q_id:
                q_row = df[df['id'] == q_id].iloc[0]
                st.markdown(f"**Text:** {q_row['text']}")
                st.markdown(f"**Marks:** {q_row['marks']} | **Year:** {q_row['year']} | **Type:** {q_row['question_type']}")
                
                with get_connection() as conn:
                    concepts = conn.execute("""
                        SELECT c.name, qc.confidence 
                        FROM question_concepts qc
                        JOIN concepts c ON qc.concept_id = c.id
                        WHERE qc.question_id = ?
                    """, (q_id,)).fetchall()
                    
                if concepts:
                    st.write("**Tagged Concepts:**")
                    for c in concepts:
                        st.write(f"- {c['name']} (Conf: {c['confidence']:.2f})")
                        
    with tab2:
        st.subheader("🎯 Exam Radar")
        st.caption("⚠️ *Disclaimer: This is pattern analysis based on historical data, NOT a prediction for future exams.*")
        
        yields = high_yield(subject_filter)
        if yields:
            y_df = pd.DataFrame(yields)
            st.write("**Top High-Yield Topics (Frequency × Marks × Recency):**")
            st.bar_chart(y_df.set_index('name')['score'])
        else:
            st.info("Not enough tagged questions to run yield analysis.")
            
        st.divider()
        st.write("**Question Archetypes**")
        archs = question_archetypes(subject_filter)
        if archs:
            st.dataframe(pd.DataFrame(archs), use_container_width=True)
            
    with tab3:
        st.subheader("🔁 Repeating Patterns")
        repeats = repeat_questions(subject_filter)
        if repeats:
            st.write(f"Found {len(repeats)} clusters of highly similar questions:")
            for i, cluster in enumerate(repeats):
                with st.expander(f"Cluster {i+1} ({len(cluster)} questions)"):
                    for q in cluster:
                        st.write(f"- **{q['year']}**: {q['text']} ({q['marks']} marks)")
        else:
            st.info("No repeated questions found in the dataset.")
