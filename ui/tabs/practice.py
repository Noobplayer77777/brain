import streamlit as st
import uuid
import pandas as pd
from datetime import datetime
from core.db import get_connection
from study.quiz import generate_quiz
from study.grading import grade_answer
from study.mastery import update_mastery

from study.mock import generate_mock, submit_mock

def render():
    st.header("🧠 Practice & Mastery")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Take Quiz", "🔁 Mistakes", "📈 Mastery Status", "⏱️ Mock Exam"])
    
    with tab1:
        st.subheader("Quiz Setup")
        subject = st.selectbox("Subject", ["DBMS", "DMGT", "Compiler Design", "Cloud Architecture Design"], key="qz_subj")
        
        col1, col2 = st.columns(2)
        with col1:
            n_questions = st.number_input("Number of Questions", min_value=1, max_value=20, value=3)
        with col2:
            mode = st.selectbox("Mode", ["pyq", "generated", "mixed"])
            
        if st.button("Start Quiz"):
            st.session_state.quiz_questions = generate_quiz(subject, n_questions, mode)
            st.session_state.quiz_index = 0
            st.session_state.quiz_results = []
            st.rerun()
            
        if 'quiz_questions' in st.session_state and st.session_state.quiz_questions:
            questions = st.session_state.quiz_questions
            idx = st.session_state.quiz_index
            
            if idx < len(questions):
                q = questions[idx]
                st.progress((idx) / len(questions))
                st.markdown(f"### Question {idx+1} of {len(questions)}")
                st.info(f"**[{q.get('marks', 2)} Marks]** {q['text']}")
                
                user_answer = st.text_area("Your Answer:", key=f"ans_{idx}")
                
                if st.button("Submit Answer"):
                    with st.spinner("Grading..."):
                        res = grade_answer(q['text'], q.get('marks', 2), user_answer, subject, q.get('model_answer'))
                        
                        st.session_state.quiz_results.append({
                            "question": q,
                            "user_answer": user_answer,
                            "grading": res
                        })
                        
                        # Save attempt to DB OUTSIDE connection
                        attempt_id = str(uuid.uuid4())
                        with get_connection() as conn:
                            c_id = None
                            if res.concept_id_to_review:
                                c_row = conn.execute("SELECT id FROM concepts WHERE subject = ? AND name LIKE ?", (subject, f"%{res.concept_id_to_review}%")).fetchone()
                                if c_row: c_id = c_row['id']
                            
                            if not c_id and not q.get('is_generated'):
                                c_row = conn.execute("SELECT concept_id FROM question_concepts WHERE question_id = ?", (q['id'],)).fetchone()
                                if c_row: c_id = c_row['concept_id']
                                
                            conn.execute("""
                                INSERT INTO attempts (id, question_id, user_answer, score, max_score, graded_by, feedback, missing_points)
                                VALUES (?, ?, ?, ?, ?, 'llm', ?, ?)
                            """, (attempt_id, q.get('id', ''), user_ans if 'user_ans' in locals() else user_answer, res.score, res.max_score, res.feedback, json.dumps(res.missing_points)))
                            
                            if c_id and "none" not in res.error_types:
                                for e_type in res.error_types:
                                    conn.execute("""
                                        INSERT INTO mistakes (id, attempt_id, concept_id, error_type, note)
                                        VALUES (hex(randomblob(16)), ?, ?, ?, ?)
                                    """, (attempt_id, c_id, e_type, res.feedback))
                                    
                        if c_id:
                            update_mastery(c_id, res.score / res.max_score, res.error_types)
                            
                    st.success("Graded!")
                    st.markdown(f"**Score:** {res.score} / {res.max_score}")
                    st.markdown(f"**Feedback:** {res.feedback}")
                    if res.missing_points:
                        st.write("**Missing Points:**")
                        for p in res.missing_points: st.write(f"- {p}")
                        
                    if st.button("Next Question"):
                        st.session_state.quiz_index += 1
                        st.rerun()
            else:
                st.success("Quiz Complete!")
                total_score = sum([r['grading'].score for r in st.session_state.quiz_results])
                total_max = sum([r['grading'].max_score for r in st.session_state.quiz_results])
                st.markdown(f"### Final Score: {total_score} / {total_max}")
                if st.button("End Review"):
                    st.session_state.quiz_questions = None
                    st.rerun()

    with tab2:
        st.subheader("🔁 Mistakes & Error Log")
        with get_connection() as conn:
            df_mistakes = pd.read_sql("""
                SELECT m.error_type, c.name as concept, m.note, m.created_at
                FROM mistakes m
                JOIN concepts c ON m.concept_id = c.id
                WHERE c.subject = ?
                ORDER BY m.created_at DESC
            """, conn, params=(subject,))
            
        if not df_mistakes.empty:
            st.dataframe(df_mistakes, use_container_width=True)
        else:
            st.info("No mistakes recorded yet! Great job.")

    with tab3:
        st.subheader("📈 Mastery Status")
        with get_connection() as conn:
            df_mastery = pd.read_sql("""
                SELECT c.name, m.score, m.attempts_count, m.next_review
                FROM mastery m
                JOIN concepts c ON m.concept_id = c.id
                WHERE c.subject = ?
            """, conn, params=(subject,))
            
        if not df_mastery.empty:
            df_mastery['next_review'] = pd.to_datetime(df_mastery['next_review'])
            now = datetime.now()
            due = df_mastery[df_mastery['next_review'] <= now]
            st.metric("Concepts Due for Review Today", len(due))
            st.write("**All Mastered Concepts:**")
            st.dataframe(df_mastery.style.background_gradient(subset=['score'], cmap='RdYlGn', vmin=0, vmax=1))
        else:
            st.info("Take a quiz to start building your mastery profile!")
            
    with tab4:
        st.subheader("⏱️ Mock Exam Mode")
        st.write("Simulate a full paper built from PYQs matching the historical archetype distribution.")
        
        m_subj = st.selectbox("Mock Subject", ["DBMS", "DMGT", "Compiler Design", "Cloud Architecture Design"], key="mk_subj")
        m_marks = st.number_input("Total Marks Target", 10, 100, 20)
        m_dur = st.number_input("Duration (Minutes)", 15, 180, 60)
        
        if st.button("Generate Mock Paper"):
            st.session_state.mock_paper = generate_mock(m_subj, m_marks)
            st.session_state.mock_responses = []
            st.session_state.mock_started = datetime.now()
            st.rerun()
            
        if 'mock_paper' in st.session_state and st.session_state.mock_paper:
            st.warning(f"Exam Started at: {st.session_state.mock_started.strftime('%H:%M:%S')}. Duration: {m_dur} min.")
            
            responses = []
            for i, q in enumerate(st.session_state.mock_paper):
                st.markdown(f"**Q{i+1} [{q['marks']} marks]:** {q['text']}")
                ans = st.text_area("Answer", key=f"mock_ans_{q['id']}")
                responses.append({"question": q, "user_answer": ans})
                
            if st.button("Submit Mock Exam"):
                with st.spinner("Grading entire mock exam with LLM..."):
                    mock_id, score, max_score, report = submit_mock(m_subj, responses, m_dur)
                    st.session_state.mock_report = {"score": score, "max_score": max_score, "report": report}
                    st.session_state.mock_paper = None
                st.success("Mock Submitted!")
                st.rerun()
                
        if 'mock_report' in st.session_state:
            rep = st.session_state.mock_report
            st.markdown(f"### Exam Complete! Score: {rep['score']} / {rep['max_score']}")
            for r in rep['report']:
                with st.expander(f"{r['question_text'][:50]}..."):
                    st.write(f"**Score:** {r['score']}/{r['max_score']}")
                    st.write(f"**Feedback:** {r['feedback']}")
                    st.write(f"**Missing:** {r['missing_points']}")
import json
