import requests
from config import OLLAMA_BASE_URL, LLM_MODEL, EMBED_MODEL

def _check_connection():
    try:
        response = requests.get(OLLAMA_BASE_URL, timeout=2)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise ConnectionError(
            f"Failed to connect to Ollama at {OLLAMA_BASE_URL}. "
            "Please ensure Ollama is running ('ollama serve')."
        ) from e

def generate(prompt: str, system: str = None, json_mode: bool = False) -> str:
    _check_connection()
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False
    }
    if system:
        payload["system"] = system
    if json_mode:
        payload["format"] = "json"
        
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Ollama generation failed: {e}")

def embed(texts: list[str]) -> list[list[float]]:
    _check_connection()
    url = f"{OLLAMA_BASE_URL}/api/embed"
    payload = {
        "model": EMBED_MODEL,
        "input": texts
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json().get("embeddings", [])
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Ollama embedding failed: {e}")

def health() -> dict:
    status = {
        "status": "offline",
        "models": [],
        "llm_model_pulled": False,
        "embed_model_pulled": False,
        "error": None
    }
    try:
        _check_connection()
        status["status"] = "online"
        
        url = f"{OLLAMA_BASE_URL}/api/tags"
        response = requests.get(url, timeout=2)
        response.raise_for_status()
        
        models = [m["name"] for m in response.json().get("models", [])]
        status["models"] = models
        status["llm_model_pulled"] = any(LLM_MODEL in m for m in models)
        status["embed_model_pulled"] = any(EMBED_MODEL in m for m in models)
    except Exception as e:
        status["error"] = str(e)
    
    return status
