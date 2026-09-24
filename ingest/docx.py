import docx

def parse_docx(file_path: str) -> list[dict]:
    doc = docx.Document(file_path)
    sections = []
    current_section = {"page_no": 1, "text": ""}
    parts = []
    
    for p in doc.paragraphs:
        if p.style.name.startswith('Heading') and parts:
            current_section["text"] = "\n".join(parts)
            sections.append(current_section)
            current_section = {"page_no": len(sections) + 1, "text": ""}
            parts = []
        
        if p.text.strip():
            parts.append(p.text.strip())
            
    if parts:
        current_section["text"] = "\n".join(parts)
        sections.append(current_section)
        
    return sections
