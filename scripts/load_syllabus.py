import argparse
from pathlib import Path
from rich.console import Console
import sys
import os

# Add project root to sys path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.db import init_db
from ingest.pdf import parse_pdf
from ingest.docx import parse_docx
from ingest.txt_md import parse_txt
from syllabus.parser import parse_syllabus, store_syllabus_tree
from syllabus.tree import auto_link_topics_to_resources

console = Console()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", required=True)
    parser.add_argument("--path", required=True)
    args = parser.parse_args()
    
    init_db()
    
    target_path = Path(args.path)
    if not target_path.exists():
        console.print(f"[red]File {target_path} not found.[/red]")
        return
        
    ext = target_path.suffix.lower()
    console.print(f"Reading {target_path}...")
    
    if ext == '.pdf':
        parsed_data = parse_pdf(str(target_path))
    elif ext == '.docx':
        parsed_data = parse_docx(str(target_path))
    elif ext in ['.txt', '.md']:
        parsed_data = parse_txt(str(target_path))
    else:
        console.print(f"[red]Unsupported extension {ext}[/red]")
        return
        
    raw_text = "\n".join([p.get('text', '') for p in parsed_data])
    
    console.print("Parsing syllabus tree with LLM... (this may take a minute)")
    try:
        tree = parse_syllabus(raw_text)
    except Exception as e:
        console.print(f"[red]Error parsing syllabus: {e}[/red]")
        return
        
    console.print("Saving tree to database...")
    store_syllabus_tree(args.subject, tree)
    
    console.print("Auto-linking resources...")
    auto_link_topics_to_resources(args.subject)
    
    console.print("[green]Syllabus loaded successfully![/green]")
    
    # Print the tree
    console.print("\n[bold]Parsed Tree:[/bold]")
    for m in tree.modules:
        console.print(f"Module: {m.title}")
        for t in m.topics:
            console.print(f"  Topic: {t.title}")

if __name__ == "__main__":
    main()
