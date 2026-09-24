import json
import uuid
from pydantic import BaseModel, Field
from typing import List, Optional
from core.db import get_connection
from core.ollama_client import generate
from rich.console import Console

console = Console()

class SubtopicModel(BaseModel):
    title: str

class TopicModel(BaseModel):
    code: Optional[str] = None
    title: str
    description: Optional[str] = None
    learning_outcomes: Optional[str] = None
    subtopics: List[SubtopicModel] = Field(default_factory=list)

class ModuleModel(BaseModel):
    code: Optional[str] = None
    title: str
    marks_weight: Optional[int] = None
    description: Optional[str] = None
    topics: List[TopicModel] = Field(default_factory=list)

class SyllabusTreeModel(BaseModel):
    modules: List[ModuleModel]

def parse_syllabus(raw_text: str) -> SyllabusTreeModel:
    schema = SyllabusTreeModel.model_json_schema()
    system_prompt = f"""You are a syllabus parser. You will receive raw syllabus text.
Extract the curriculum structure into a strict JSON object that matches this schema exactly:
{json.dumps(schema)}
Do not output anything except the valid JSON object.
"""
    
    prompt = f"Raw Syllabus Text:\n{raw_text}"
    
    # Try twice
    for attempt in range(2):
        try:
            resp = generate(prompt, system=system_prompt, json_mode=True)
            data = json.loads(resp)
            return SyllabusTreeModel.model_validate(data)
        except Exception as e:
            if attempt == 1:
                console.print(f"[red]Failed to parse syllabus JSON after 2 attempts: {e}[/red]")
                raise
            else:
                prompt += f"\n\nPrevious attempt failed with error: {e}. Please fix and return strictly valid JSON matching the schema."

def store_syllabus_tree(subject: str, tree: SyllabusTreeModel):
    with get_connection() as conn:
        # Delete existing tree for this subject
        # Because of ON DELETE CASCADE, deleting modules will delete topics and subtopics (if supported in sqlite via pragma)
        # We also manually delete to be safe
        modules_to_delete = conn.execute("SELECT id FROM modules WHERE subject = ?", (subject,)).fetchall()
        for mod in modules_to_delete:
            topics_to_delete = conn.execute("SELECT id FROM topics WHERE module_id = ?", (mod['id'],)).fetchall()
            for top in topics_to_delete:
                conn.execute("DELETE FROM subtopics WHERE topic_id = ?", (top['id'],))
                conn.execute("DELETE FROM topic_resources WHERE topic_id = ?", (top['id'],))
            conn.execute("DELETE FROM topics WHERE module_id = ?", (mod['id'],))
        conn.execute("DELETE FROM modules WHERE subject = ?", (subject,))
        
        # Insert new tree
        for m_idx, mod in enumerate(tree.modules):
            m_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO modules (id, subject, code, title, order_index, marks_weight, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (m_id, subject, mod.code, mod.title, m_idx, mod.marks_weight, mod.description))
            
            for t_idx, top in enumerate(mod.topics):
                t_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO topics (id, module_id, code, title, order_index, description, learning_outcomes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (t_id, m_id, top.code, top.title, t_idx, top.description, top.learning_outcomes))
                
                for s_idx, sub in enumerate(top.subtopics):
                    s_id = str(uuid.uuid4())
                    conn.execute("""
                        INSERT INTO subtopics (id, topic_id, title, order_index)
                        VALUES (?, ?, ?, ?)
                    """, (s_id, t_id, sub.title, s_idx))
