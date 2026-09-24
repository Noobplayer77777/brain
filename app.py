import streamlit as st
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ui.tabs import dashboard, library, chat, syllabus, coverage, questions, practice, plan, settings
from core.db import init_db

init_db()

st.set_page_config(page_title="Exam Brain", layout="wide")
st.title("🧠 Exam Brain")

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊 Dashboard", "📅 Plan", "Library", "💬 Ask", "🗺️ Syllabus", "📊 Coverage", "📝 Questions", "🧠 Practice"
])

with tab1:
    dashboard.render()

with tab2:
    plan.render()

with tab3:
    library.render()

with tab4:
    chat.render()

with tab5:
    syllabus.render()

with tab6:
    coverage.render()

with tab7:
    questions.render()

with tab8:
    practice.render()

# Sidebar for Settings (so it's out of the way)
with st.sidebar:
    settings.render()
