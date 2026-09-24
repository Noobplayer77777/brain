import json
from core.ollama_client import generate
from core.retrieval import Hit

def answer_question(question: str, hits: list[Hit]) -> dict:
    context_blocks = []
    for i, h in enumerate(hits):
        loc = f"p.{h.page}" if h.page else f"slide {h.slide}" if h.slide else ""
        context_blocks.append(f"--- Document [{i+1}]: {h.filename} {loc} (Chunk ID: {h.chunk_id}) ---\n{h.text}\n")
    
    context_str = "\n".join(context_blocks)
    
    system_prompt = """You are Exam Brain, an AI study assistant.
Answer the user's question using ONLY the provided context.
If the context does not contain enough information to answer the question fully, state explicitly what is missing and answer what you can. If you cannot answer at all, say so explicitly.
DO NOT invent or hallucinate information.
Use proper LaTeX formatting ($...$ for inline, $$...$$ for block) for any math or formulas.
For every claim or piece of information you provide, append a citation in the format [filename, p.X] or [filename, slide Y]. DO NOT invent page numbers.

You MUST respond in valid JSON format matching this schema exactly:
{
    "answer_markdown": "Your detailed answer here...",
    "citations": [
        {"filename": "...", "page": "...", "chunk_id": "..."}
    ],
    "confidence": "low" | "medium" | "high",
    "missing_info": "Explain what is missing, or null if fully answered"
}
"""
    
    prompt = f"CONTEXT:\n{context_str}\n\nQUESTION: {question}"
    
    response_text = generate(prompt, system=system_prompt, json_mode=True)
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        return {
            "answer_markdown": "Error parsing JSON from LLM. Raw output:\n\n" + response_text,
            "citations": [],
            "confidence": "low",
            "missing_info": "JSON Parse Error"
        }
