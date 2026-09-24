import re
import uuid

def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    # Split by sentence boundaries approximately
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = []
    current_len = 0
    
    for s in sentences:
        s_len = len(s)
        if current_len + s_len > chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            
            # Apply overlap
            overlap_len = 0
            overlap_chunk = []
            for prev_s in reversed(current_chunk):
                if overlap_len + len(prev_s) <= chunk_overlap:
                    overlap_chunk.insert(0, prev_s)
                    overlap_len += len(prev_s) + 1
                else:
                    break
            if not overlap_chunk: # fallback if a single sentence is huge
                overlap_chunk = [current_chunk[-1]]
                
            current_chunk = overlap_chunk
            current_len = sum(len(x) for x in current_chunk) + len(current_chunk)
            
        current_chunk.append(s)
        current_len += s_len + 1
        
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks

def generate_chunks(parsed_data: list[dict], resource_id: str, chunk_size=800, chunk_overlap=150) -> list[dict]:
    final_chunks = []
    chunk_index = 0
    
    for item in parsed_data:
        text = item.get("text", "")
        if not text:
            continue
            
        text_chunks = chunk_text(text, chunk_size, chunk_overlap)
        
        for tc in text_chunks:
            if not tc.strip(): continue
            char_count = len(tc)
            token_count = char_count // 4  # approx based on chars/4
            
            chunk = {
                "chunk_id": str(uuid.uuid4()),
                "resource_id": resource_id,
                "chunk_index": chunk_index,
                "text": tc,
                "page_start": item.get("page_no"),
                "page_end": item.get("page_no"),
                "slide_no": item.get("slide_no"),
                "token_count": token_count,
                "char_count": char_count
            }
            final_chunks.append(chunk)
            chunk_index += 1
            
    return final_chunks
