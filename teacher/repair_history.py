
import os
import json
from pathlib import Path
from backend.database import db

def repair_history():
    print("Repairing Student History...")
    students = db.get_all_students()
    
    for student in students:
        sid = student["id"]
        print(f"Checking Student {sid}...")
        
        student_dir = Path(f"data/students/{sid}")
        if not student_dir.exists():
            continue
            
        rebuilt_history = []
        
        # Walk through all course folders
        for course_dir in student_dir.iterdir():
            if not course_dir.is_dir() or course_dir.name in ["history.json"]:
                continue
            
            course_id = course_dir.name
            
            # Walk through all quiz folders
            for quiz_dir in course_dir.glob("quiz_*"):
                try:
                    quiz_num = int(quiz_dir.name.split("_")[1])
                    correction_path = quiz_dir / "correction.json"
                    
                    if correction_path.exists():
                        with open(correction_path, "r") as f:
                            correction = json.load(f)
                            
                        entry = {
                            "quiz_number": quiz_num,
                            "course_id": course_id,
                            "timestamp": correction_path.stat().st_mtime,
                            "correction": correction
                        }
                        rebuilt_history.append(entry)
                        print(f"  Found Quiz #{quiz_num} ({course_id}) - Added.")
                except Exception as e:
                    print(f"  Skipping {quiz_dir}: {e}")
                    
        # Sort by timestamp
        rebuilt_history.sort(key=lambda x: x["timestamp"])
        
        # Save
        history_path = student_dir / "history.json"
        
        # Merge with existing weak_concepts if we want to keep them? 
        # Actually weak_concepts are legacy. We can just overwrite past_quizzes.
        current_data = db.get_student_history(sid)
        current_data["past_quizzes"] = rebuilt_history
        
        with open(history_path, "w") as f:
            json.dump(current_data, f, indent=2)
            
        print(f"Saved {len(rebuilt_history)} quizzes to history for {sid}.")

if __name__ == "__main__":
    repair_history()
