import json
from pathlib import Path

def migrate_file(filepath: Path):
    if not filepath.exists():
        print(f"Skipping {filepath}, does not exist.")
        return
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        modified = False
        for student in data:
            if "name" in student:
                del student["name"]
                modified = True
                
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Successfully migrated {filepath}.")
        else:
            print(f"No changes needed for {filepath}.")
            
    except Exception as e:
        print(f"Error migrating {filepath}: {e}")

if __name__ == "__main__":
    teacher_db = Path("/home/emmanuel/LeRépétiteur/teacher/data/global/students.json")
    student_db = Path("/home/emmanuel/LeRépétiteur/student/data/global/students.json")
    
    print("Starting migration...")
    migrate_file(teacher_db)
    migrate_file(student_db)
    print("Migration complete.")
