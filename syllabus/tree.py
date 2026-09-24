from core.db import get_connection
from difflib import SequenceMatcher
import uuid

def get_tree(subject: str) -> list:
    tree = []
    with get_connection() as conn:
        modules = conn.execute("SELECT * FROM modules WHERE subject = ? ORDER BY order_index ASC", (subject,)).fetchall()
        for m in modules:
            mod_dict = dict(m)
            mod_dict['topics'] = []
            
            topics = conn.execute("SELECT * FROM topics WHERE module_id = ? ORDER BY order_index ASC", (m['id'],)).fetchall()
            for t in topics:
                top_dict = dict(t)
                
                subtopics = conn.execute("SELECT * FROM subtopics WHERE topic_id = ? ORDER BY order_index ASC", (t['id'],)).fetchall()
                top_dict['subtopics'] = [dict(s) for s in subtopics]
                
                mod_dict['topics'].append(top_dict)
                
            tree.append(mod_dict)
            
    return tree

def flatten_topics(subject: str) -> list:
    flat = []
    tree = get_tree(subject)
    for mod in tree:
        for top in mod['topics']:
            flat.append({
                "module_title": mod['title'],
                "topic_id": top['id'],
                "topic_title": top['title']
            })
    return flat

def topic_by_id(topic_id: str) -> dict:
    with get_connection() as conn:
        t = conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
        return dict(t) if t else None

def auto_link_topics_to_resources(subject: str):
    """
    Fuzzy matches topic titles against resource filenames or chunk text
    to seed the topic_resources table.
    """
    topics = flatten_topics(subject)
    if not topics: return
    
    with get_connection() as conn:
        resources = conn.execute("SELECT id, filename FROM resources WHERE subject = ?", (subject,)).fetchall()
        
        for t in topics:
            best_res = None
            best_score = 0.0
            t_title = t['topic_title'].lower()
            
            for r in resources:
                r_name = r['filename'].lower()
                score = SequenceMatcher(None, t_title, r_name).ratio()
                
                if score > best_score:
                    best_score = score
                    best_res = r['id']
                    
            if best_res and best_score > 0.3:
                # Store suggestion
                conn.execute("""
                    INSERT OR REPLACE INTO topic_resources (topic_id, resource_id, relevance)
                    VALUES (?, ?, ?)
                """, (t['topic_id'], best_res, 0.5))

# CRUD Operations for UI
def update_module_title(module_id: str, new_title: str):
    with get_connection() as conn:
        conn.execute("UPDATE modules SET title = ? WHERE id = ?", (new_title, module_id))

def update_topic_title(topic_id: str, new_title: str):
    with get_connection() as conn:
        conn.execute("UPDATE topics SET title = ? WHERE id = ?", (new_title, topic_id))

def update_subtopic_title(subtopic_id: str, new_title: str):
    with get_connection() as conn:
        conn.execute("UPDATE subtopics SET title = ? WHERE id = ?", (new_title, subtopic_id))

def swap_module_order(subject: str, idx1: int, idx2: int):
    with get_connection() as conn:
        mods = conn.execute("SELECT id, order_index FROM modules WHERE subject = ? ORDER BY order_index ASC", (subject,)).fetchall()
        if 0 <= idx1 < len(mods) and 0 <= idx2 < len(mods):
            id1 = mods[idx1]['id']
            id2 = mods[idx2]['id']
            
            # Temporary value to swap securely
            conn.execute("UPDATE modules SET order_index = -1 WHERE id = ?", (id1,))
            conn.execute("UPDATE modules SET order_index = ? WHERE id = ?", (mods[idx1]['order_index'], id2))
            conn.execute("UPDATE modules SET order_index = ? WHERE id = ?", (mods[idx2]['order_index'], id1))
