import json
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from core.ollama_client import generate
from core.retrieval import hybrid_search

class GradingResult(BaseModel):
    score: float
    max_score: float
    missing_points: List[str]
    error_types: List[Literal["conceptual", "factual", "procedural", "calculation", "presentation", "misread", "incomplete", "none"]]
    feedback: str
    concept_id_to_review: Optional[str] = None

def grade_answer(question_text: str, max_marks: int, user_answer: str, subject: str, model_answer: str = None) -> GradingResult:
    context = ""
    if model_answer:
        context = f"Model Answer/Rubric:\n{model_answer}"
    else:
        # Ground grading in retrieved chunks if no model answer exists
        hits = hybrid_search(question_text, subject=subject, k=3)
        context = "Reference Material:\n" + "\n".join([h.text for h in hits])
        
    schema = GradingResult.model_json_schema()
    sys_prompt = f"""You are a strict but fair professor grading an exam.
Compare the user's answer to the reference context/model answer.
Assign a score out of {max_marks}.
Classify any errors into the predefined error types (or 'none' if perfectly correct).
Provide actionable feedback pointing exactly to what is missing.
If a specific concept was misunderstood, return its name or a short phrase in concept_id_to_review.
Return strict JSON matching this schema:
{json.dumps(schema)}
"""
    prompt = f"Question: {question_text}\nMax Marks: {max_marks}\n{context}\n\nUser Answer:\n{user_answer}"
    
    for attempt in range(2):
        try:
            resp = generate(prompt, system=sys_prompt, json_mode=True)
            data = json.loads(resp)
            res = GradingResult.model_validate(data)
            # Ensure score does not exceed max_score
            res.score = min(res.score, float(max_marks))
            res.max_score = float(max_marks)
            return res
        except Exception as e:
            if attempt == 1:
                return GradingResult(score=0, max_score=max_marks, missing_points=["Grading failed"], error_types=["incomplete"], feedback="Error grading answer.")
            prompt += f"\nError: {e}. Fix JSON."
