import streamlit as st
from syllabus.tree import get_tree, update_module_title, update_topic_title, update_subtopic_title, swap_module_order

def render():
    st.header("🗺️ Syllabus Tree")
    
    subject_filter = st.selectbox("Subject", ["DBMS", "DMGT", "Compiler Design", "Cloud Architecture Design"])
    
    tree = get_tree(subject_filter)
    
    if not tree:
        st.info(f"No syllabus loaded for {subject_filter}. Use the CLI to load one.")
        return
        
    for m_idx, mod in enumerate(tree):
        with st.expander(f"Module {m_idx+1}: {mod['title']}", expanded=False):
            col1, col2, col3 = st.columns([8, 1, 1])
            with col1:
                new_m_title = st.text_input("Module Name", value=mod['title'], key=f"m_{mod['id']}")
                if new_m_title != mod['title']:
                    update_module_title(mod['id'], new_m_title)
                    st.rerun()
            with col2:
                if st.button("⬆️", key=f"m_up_{mod['id']}") and m_idx > 0:
                    swap_module_order(subject_filter, m_idx, m_idx - 1)
                    st.rerun()
            with col3:
                if st.button("⬇️", key=f"m_down_{mod['id']}") and m_idx < len(tree) - 1:
                    swap_module_order(subject_filter, m_idx, m_idx + 1)
                    st.rerun()
                    
            st.caption(f"Coverage: placeholder")
                    
            for t_idx, top in enumerate(mod['topics']):
                st.markdown(f"**Topic {t_idx+1}:**")
                new_t_title = st.text_input("Topic Name", value=top['title'], key=f"t_{top['id']}", label_visibility="collapsed")
                if new_t_title != top['title']:
                    update_topic_title(top['id'], new_t_title)
                    st.rerun()
                    
                for s_idx, sub in enumerate(top['subtopics']):
                    new_s_title = st.text_input("Subtopic", value=sub['title'], key=f"s_{sub['id']}", label_visibility="collapsed")
                    if new_s_title != sub['title']:
                        update_subtopic_title(sub['id'], new_s_title)
                        st.rerun()
                st.divider()
