# Exam Brain

Exam Brain is a local AI study system for a university student. It runs fully offline with a lightweight architecture.

## Setup Instructions

1. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   ```

2. **Install requirements**:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: This keeps the install size under ~600MB as no PyTorch/LangChain packages are included.)*

3. **Install Ollama & Pull Models**:
   Ensure [Ollama](https://ollama.com) is installed and running (`ollama serve`).
   Pull the required models:
   ```bash
   ollama pull qwen2.5:7b-instruct-q4_K_M
   ollama pull nomic-embed-text
   ```

4. **Run the Health Check**:
   ```bash
   python scripts/health_check.py
   ```
   This script verifies that Ollama is online, models are pulled, disk space is adequate, SQLite is writable, and ChromaDB is importable.

5. **Run the App**:
   *(Coming soon in Phase 1)*
   ```bash
   streamlit run app.py
   ```
