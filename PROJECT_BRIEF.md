# Exam Brain

Exam Brain is a fully local AI study system designed specifically for a university student. It processes study materials, extracts concepts, parses syllabus topics, and acts as an interactive study companion, running entirely on a local machine without internet dependencies.

## Key Features
- **Local Inference**: Uses Ollama for LLM and embeddings generation to ensure data privacy and work entirely offline.
- **Efficient Architecture**: Designed for CPU inference without PyTorch/LangChain overhead, ensuring low memory footprint and compatibility with an Intel Core Ultra 5 machine.
- **Subject Optimization**: Handles technical domains such as Database Management Systems (SQL), Discrete Mathematics & Graph Theory (LaTeX rendering), Compiler Design (automata notation), and Cloud Architecture Design.
- **Reliable Storage**: Uses SQLite as the single source of truth for structured data (incorporating FTS5 keyword search) and ChromaDB for semantic search.

## Constraints & Design
- Hardware: Intel Arc iGPU (no CUDA/NVIDIA), 16GB RAM, limited disk space (~24GB free).
- Lightweight Dependencies: Relies on `requests` to talk to Ollama instead of heavy frameworks.
- UI: Clean and minimal Streamlit application with a dark theme.
- Data Processing: Handles PDFs via PyMuPDF, PPTX via python-pptx, DOCX via python-docx, and optical character recognition (OCR) via pytesseract where needed.

## Setup
Refer to `README.md` for environment setup, requirements installation, model preparation, and health check instructions.
