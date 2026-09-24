import shutil
import os
from datetime import datetime

def create_backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backups/exam_brain_backup_{timestamp}"
    
    os.makedirs(backup_dir, exist_ok=True)
    
    # Backup DB
    if os.path.exists("data/exam_brain.db"):
        shutil.copy2("data/exam_brain.db", backup_dir)
        
    # Backup Chroma
    if os.path.exists("data/chroma"):
        shutil.copytree("data/chroma", f"{backup_dir}/chroma")
        
    # Zip it
    shutil.make_archive(backup_dir, 'zip', backup_dir)
    
    # Cleanup unzipped folder
    shutil.rmtree(backup_dir)
    print(f"Backup created successfully: {backup_dir}.zip")
    return f"{backup_dir}.zip"

if __name__ == "__main__":
    create_backup()
