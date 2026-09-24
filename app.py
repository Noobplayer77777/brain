import streamlit as st
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ui.tabs import library, chat, syllabus, coverage
from core.db import init_db

init_db()

st.set_page_config(page_title="Exam Brain", layout="wide")
st.title("🧠 Exam Brain")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Library", "💬 Ask", "🗺️ Syllabus", "📊 Coverage", "Settings"])

with tab1:
    library.render()

with tab2:
    chat.render()

with tab3:
    syllabus.render()

with tab4:
    coverage.render()

with tab5:
    st.info("Settings tab coming soon")
