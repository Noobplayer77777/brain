import streamlit as st
import pandas as pd
from core.db import get_connection
from ingest.pipeline import ingest_file
import chromadb
from config import CHROMA_DIR
from pathlib import Path

def render():
    st.header("Resource Library")
    
    with get_connection() as conn:
        df = pd.read_sql("""
            SELECT r.id, r.filename, r.subject, r.filetype, r.num_pages, 
                   COUNT(c.id) as chunks, r.status, r.added_at
            FROM resources r
            LEFT JOIN chunks c ON r.id = c.resource_id
            GROUP BY r.id
        """, conn)
    
    if df.empty:
        st.info("No resources ingested yet. Use the CLI to ingest files.")
    else:
        st.dataframe(df, use_container_width=True)
        
        selected_id = st.selectbox("Select a resource to re-ingest", df['id'].tolist(), format_func=lambda x: df[df['id'] == x]['filename'].values[0])
        if st.button("Re-ingest"):
            with get_connection() as conn:
                res = conn.execute("SELECT path, subject FROM resources WHERE id = ?", (selected_id,)).fetchone()
            
            if res:
                with st.spinner("Re-ingesting..."):
                    # Drop status to allow re-ingest
                    with get_connection() as conn:
                        conn.execute("UPDATE resources SET status = 'pending' WHERE id = ?", (selected_id,))
                    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
                    collection = chroma_client.get_or_create_collection("exam_brain")
                    result = ingest_file(Path(res['path']), res['subject'], collection)
                    if result['status'] == 'done':
                        st.success("Re-ingestion complete!")
                    else:
                        st.error(f"Re-ingestion failed: {result.get('reason')}")
                    st.rerun()
