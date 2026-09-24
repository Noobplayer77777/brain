import streamlit as st
import os
import subprocess
from core.db import get_connection

def render():
    st.header("⚙️ Settings & Administration")
    
    st.subheader("Exam Dates")
    subjects = ["DBMS", "DMGT", "Compiler Design", "Cloud Architecture Design"]
    
    with get_connection() as conn:
        for s in subjects:
            existing = conn.execute("SELECT value FROM settings WHERE key = ?", (f"exam_date_{s}",)).fetchone()
            val = existing['value'] if existing else None
            
            new_date = st.date_input(f"{s} Exam Date", value=None)
            if st.button(f"Save {s} Date"):
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (f"exam_date_{s}", new_date.isoformat()))
                st.success(f"Saved {new_date}")
                
    st.divider()
    st.subheader("Data Management")
    if st.button("Create Backup"):
        with st.spinner("Zipping database and Chroma..."):
            try:
                # call the backup script
                subprocess.run([os.sys.executable, "scripts/backup.py"], check=True)
                st.success("Backup created successfully in backups/ folder!")
            except Exception as e:
                st.error(f"Backup failed: {e}")
