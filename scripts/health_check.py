import sys
import os
import shutil

# Add the parent directory to sys.path so we can import from core and config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rich.console import Console
from core.ollama_client import health
from config import DB_PATH
from core.db import init_db

console = Console()

def check_disk_space():
    total, used, free = shutil.disk_usage("/")
    free_gb = free // (2**30)
    if free_gb < 10:
        console.print(f"[yellow]⚠ Disk Space: Low ({free_gb} GB free)[/yellow]")
    else:
        console.print(f"[green]✔ Disk Space: OK ({free_gb} GB free)[/green]")
    return free_gb

def check_sqlite():
    try:
        init_db()
        console.print("[green]✔ SQLite: Writable and initialized[/green]")
    except Exception as e:
        console.print(f"[red]✖ SQLite: Error - {e}[/red]")
        return False
    return True

def check_chromadb():
    try:
        import chromadb
        console.print("[green]✔ ChromaDB: Importable[/green]")
    except ImportError:
        console.print("[red]✖ ChromaDB: Not installed (run pip install -r requirements.txt)[/red]")
        return False
    except Exception as e:
        console.print(f"[red]✖ ChromaDB: Error - {e}[/red]")
        return False
    return True

def check_ollama():
    status = health()
    if status["status"] == "online":
        console.print("[green]✔ Ollama API: Online[/green]")
    else:
        console.print(f"[red]✖ Ollama API: Offline ({status.get('error')})[/red]")
        console.print("[yellow]  Please run 'ollama serve'[/yellow]")
        return False
        
    all_good = True
    if status["llm_model_pulled"]:
        console.print("[green]✔ LLM Model: Present[/green]")
    else:
        console.print("[red]✖ LLM Model: Missing[/red]")
        console.print("[yellow]  Please run: ollama pull qwen2.5:7b-instruct-q4_K_M[/yellow]")
        all_good = False
        
    if status["embed_model_pulled"]:
        console.print("[green]✔ Embed Model: Present[/green]")
    else:
        console.print("[red]✖ Embed Model: Missing[/red]")
        console.print("[yellow]  Please run: ollama pull nomic-embed-text[/yellow]")
        all_good = False
        
    return all_good

def main():
    console.print("[bold cyan]--- Exam Brain Health Check ---[/bold cyan]")
    
    disk_ok = check_disk_space() > 2 # At least 2GB
    sqlite_ok = check_sqlite()
    chroma_ok = check_chromadb()
    ollama_ok = check_ollama()
    
    if disk_ok and sqlite_ok and chroma_ok and ollama_ok:
        console.print("\n[bold green]All systems nominal! Ready to study.[/bold green]")
        sys.exit(0)
    else:
        console.print("\n[bold red]Health check failed. Please resolve the issues above.[/bold red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
