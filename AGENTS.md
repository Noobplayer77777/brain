PROJECT: "Exam Brain" — a fully local AI study system for a university student.

HARDWARE CONSTRAINTS (hard limits — never violate):
- Intel Core Ultra 5 125H, 16 GB RAM, Intel Arc integrated GPU (no NVIDIA, no CUDA).
- Windows laptop. Storage is nearly full (~24 GB free). Keep all dependencies lean.
- Inference runs on CPU via Ollama. Expect 5–15 tokens/sec. Design for patience, not speed.

ARCHITECTURE RULES:
- LLM + embeddings via local Ollama HTTP API (http://localhost:11434). NEVER use OpenAI/Anthropic APIs.
- Models: `qwen2.5:7b-instruct-q4_K_M` for generation, `nomic-embed-text` for embeddings.
- DO NOT install PyTorch, sentence-transformers, transformers, LangChain, LlamaIndex, or Unstructured. They are too heavy. Use raw HTTP calls to Ollama instead.
- Vector store: ChromaDB (persistent local client).
- Relational store: SQLite (single file). This is the source of truth for all structured data.
- Keyword search: SQLite FTS5.
- UI: Streamlit, dark theme, clean and minimal.
- Parsing: PyMuPDF (PDF), python-pptx (PPTX), python-docx (DOCX). Tesseract via pytesseract only when a PDF has no text layer.
- Everything must run offline after setup. No telemetry, no cloud.

SUBJECTS: DBMS, DMGT (Discrete Maths & Graph Theory), Compiler Design, Cloud Architecture Design.
Note: DMGT needs LaTeX rendering. Compiler Design has grammar/automata notation. DBMS has SQL. Plan extraction prompts accordingly.

ENGINEERING RULES:
- Python 3.11+, type hints, dataclasses, small focused modules.
- Every LLM extraction must use a strict JSON schema and validate the output. Retry once on parse failure, then log and skip.
- Never silently swallow errors — log to `logs/` and surface in the UI.
- Every retrieved answer must cite source file + page/slide number.
- Do not build features from future phases. Stay in scope.
- Commit at the end of each phase with a clear message.

FOLDER STRUCTURE (target):
exam_brain/
  app.py                  # Streamlit entry
  config.py               # paths, model names, constants
  core/                   # db.py, ollama_client.py, embeddings.py, retrieval.py, llm.py
  ingest/                 # pipeline.py, pdf.py, pptx.py, docx.py, chunker.py, ocr.py
  syllabus/               # parser.py, tree.py
  concepts/               # extractor.py, linker.py, coverage.py
  questions/              # parser.py, tagger.py, analytics.py
  study/                  # quiz.py, grading.py, mastery.py, planner.py
  ui/                     # tabs, components
  data/                   # exam_brain.db, chroma/, raw/, processed/
  logs/
  requirements.txt
  PROJECT_BRIEF.md
  AGENTS.md