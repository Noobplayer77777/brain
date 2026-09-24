import streamlit as st
import time
from core.retrieval import hybrid_search, expand_query
from core.llm import answer_question
from config import LLM_MODEL, EMBED_MODEL

def render():
    st.markdown("""
    <style>
        .stChatMessage { border-radius: 10px; padding: 10px; margin-bottom: 10px; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; margin-bottom: 10px; display: inline-block; }
        .badge-high { background-color: #1b5e20; color: white; }
        .badge-medium { background-color: #f57f17; color: white; }
        .badge-low { background-color: #b71c1c; color: white; }
        code { font-family: 'Courier New', monospace; }
    </style>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.header("Search Settings")
        subject_filter = st.selectbox("Subject", ["All", "DBMS", "DMGT", "Compiler Design", "Cloud Architecture Design"])
        k_slider = st.slider("Retrieval K (Chunks)", min_value=2, max_value=20, value=8)
        use_expand = st.toggle("Expand Query (LLM Paraphrase)", value=False)
        
        st.divider()
        st.caption(f"**LLM:** {LLM_MODEL}")
        st.caption(f"**Embed:** {EMBED_MODEL}")
        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.rerun()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if "confidence" in msg:
                badge_class = f"badge-{msg['confidence'].lower()}" if msg['confidence'].lower() in ["low", "medium", "high"] else "badge-low"
                st.markdown(f"<span class='badge {badge_class}'>Confidence: {msg['confidence'].upper()}</span>", unsafe_allow_html=True)
            
            st.markdown(msg["content"])
            
            if msg.get("missing_info"):
                st.info(f"**Missing Info:** {msg['missing_info']}")
                
            if msg.get("sources"):
                with st.expander("Sources"):
                    for c in msg["sources"]:
                        st.write(f"- {c.get('filename')} (Page: {c.get('page')})")
                        
            if msg.get("retrieval_inspect"):
                with st.expander("🔍 Inspect Retrieval"):
                    for idx, h in enumerate(msg["retrieval_inspect"]):
                        st.markdown(f"**{idx+1}. {h['filename']} (Score: {h['score']:.4f})**")
                        st.text(h['text'])

    if prompt := st.chat_input("Ask a question about your materials..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.chat_message("assistant"):
            with st.spinner("Searching and thinking..."):
                start_time = time.time()
                
                search_query = prompt
                if use_expand:
                    search_query = expand_query(prompt)
                    
                hits = hybrid_search(search_query, subject=subject_filter, k=k_slider)
                
                if not hits:
                    st.warning("No relevant documents found in the library.")
                    ans_data = {
                        "answer_markdown": "I couldn't find any relevant context in the study materials.",
                        "citations": [],
                        "confidence": "low",
                        "missing_info": "No documents retrieved."
                    }
                else:
                    ans_data = answer_question(prompt, hits)
                    
                elapsed = time.time() - start_time
                
                ans = ans_data.get("answer_markdown", "")
                conf = ans_data.get("confidence", "low")
                missing = ans_data.get("missing_info", None)
                cits = ans_data.get("citations", [])
                
                badge_class = f"badge-{conf.lower()}" if conf.lower() in ["low", "medium", "high"] else "badge-low"
                st.markdown(f"<span class='badge {badge_class}'>Confidence: {conf.upper()}</span>", unsafe_allow_html=True)
                st.markdown(ans)
                
                if missing:
                    st.info(f"**Missing Info:** {missing}")
                    
                if cits:
                    with st.expander("Sources"):
                        for c in cits:
                            st.write(f"- {c.get('filename')} (p. {c.get('page')})")
                            
                with st.expander("🔍 Inspect Retrieval"):
                    for idx, h in enumerate(hits):
                        st.markdown(f"**{idx+1}. {h.filename} (Score: {h.score:.4f})**")
                        st.text(h.text)
                        
                st.caption(f"Response time: {elapsed:.2f}s")
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": ans,
                    "confidence": conf,
                    "missing_info": missing,
                    "sources": cits,
                    "retrieval_inspect": [{"filename": h.filename, "score": h.score, "text": h.text} for h in hits]
                })
