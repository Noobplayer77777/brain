import streamlit as st
from concepts.coverage import get_coverage_matrix
from core.db import get_connection

def render():
    st.header("📊 Coverage Matrix")
    
    subject_filter = st.selectbox("Select Subject", ["DBMS", "DMGT", "Compiler Design", "Cloud Architecture Design"], key="cov_subj")
    
    df = get_coverage_matrix(subject_filter)
    
    if df.empty:
        st.info("No concepts extracted yet. Run the extraction and linking scripts.")
        return
        
    tab1, tab2 = st.tabs(["Coverage Matrix", "🔗 Prerequisites"])
    
    with tab1:
        st.markdown("""
        <style>
        .status-blind { background-color: #ffcccc; color: #b30000; padding: 4px; border-radius: 4px; }
        .status-thin { background-color: #ffeebf; color: #b37700; padding: 4px; border-radius: 4px; }
        .status-covered { background-color: #ccffcc; color: #008000; padding: 4px; border-radius: 4px; }
        </style>
        """, unsafe_allow_html=True)
        
        status_filter = st.multiselect("Filter Status", ["covered", "thin", "blind"], default=["covered", "thin", "blind"])
        
        filtered_df = df[df['status'].isin(status_filter)]
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.dataframe(filtered_df[['concept_name', 'type', 'status', 'num_resources', 'num_questions', 'topics']], use_container_width=True)
            
        with col2:
            st.subheader("Concept Details")
            selected_concept = st.selectbox("Select Concept to inspect", filtered_df['concept_name'].tolist())
            if selected_concept:
                c_row = filtered_df[filtered_df['concept_name'] == selected_concept].iloc[0]
                st.markdown(f"**Name:** {c_row['concept_name']}")
                st.markdown(f"**Type:** {c_row['type']}")
                st.markdown(f"**Status:** {c_row['status']}")
                st.markdown(f"**Topics:** {c_row['topics']}")
                
                with get_connection() as conn:
                    desc = conn.execute("SELECT definition FROM concepts WHERE id = ?", (c_row['concept_id'],)).fetchone()
                    if desc:
                        st.info(desc[0])
                        
                    res = conn.execute("""
                        SELECT r.filename, cr.relation, cr.confidence, c.text 
                        FROM concept_resources cr
                        JOIN resources r ON cr.resource_id = r.id
                        JOIN chunks c ON cr.chunk_id = c.chunk_id
                        WHERE cr.concept_id = ?
                    """, (c_row['concept_id'],)).fetchall()
                    
                if res:
                    st.write("**Linked Resources:**")
                    for r in res:
                        with st.expander(f"{r['filename']} ({r['relation']})"):
                            st.caption(f"Confidence: {r['confidence']}")
                            st.text(r['text'])
                else:
                    st.write("No resources linked.")

    with tab2:
        st.subheader("Prerequisites Management")
        st.info("Manual editing of prerequisite edges.")
        
        c_names = df['concept_name'].tolist()
        c_map = {name: cid for name, cid in zip(df['concept_name'], df['concept_id'])}
        
        c_source = st.selectbox("Source Concept", c_names, key="prereq_src")
        c_target = st.selectbox("Requires Prerequisite", c_names, key="prereq_tgt")
        
        if st.button("Add Prerequisite"):
            if c_source and c_target and c_source != c_target:
                with get_connection() as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO prerequisites (concept_id, prereq_concept_id, source, confidence)
                        VALUES (?, ?, 'user', 1.0)
                    """, (c_map[c_source], c_map[c_target]))
                st.success("Added prerequisite!")
                st.rerun()
                
        # List existing
        st.write("**Existing Prerequisites:**")
        with get_connection() as conn:
            existing = conn.execute("""
                SELECT p.concept_id, c1.name as src_name, p.prereq_concept_id, c2.name as tgt_name, p.source
                FROM prerequisites p
                JOIN concepts c1 ON p.concept_id = c1.id
                JOIN concepts c2 ON p.prereq_concept_id = c2.id
                JOIN concepts c_all ON c1.subject = c_all.subject
                WHERE c1.subject = ?
                GROUP BY p.concept_id, p.prereq_concept_id
            """, (subject_filter,)).fetchall()
            
        for e in existing:
            col_a, col_b = st.columns([4, 1])
            with col_a:
                st.write(f"**{e['src_name']}** requires **{e['tgt_name']}** (Source: {e['source']})")
            with col_b:
                if st.button("❌", key=f"del_prereq_{e['concept_id']}_{e['prereq_concept_id']}"):
                    with get_connection() as conn:
                        conn.execute("DELETE FROM prerequisites WHERE concept_id = ? AND prereq_concept_id = ?", (e['concept_id'], e['prereq_concept_id']))
                    st.rerun()
