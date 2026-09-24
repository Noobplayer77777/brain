import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DB_PATH = DATA_DIR / "exam_brain.db"
CHROMA_DIR = DATA_DIR / "chroma"
LOG_DIR = BASE_DIR / "logs"

# Ensure directories exist
for d in [DATA_DIR, RAW_DIR, PROCESSED_DIR, CHROMA_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = "qwen2.5:7b-instruct-q4_K_M"
EMBED_MODEL = "nomic-embed-text"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# OCR App Config
TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
