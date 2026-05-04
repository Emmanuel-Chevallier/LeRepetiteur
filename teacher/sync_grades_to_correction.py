import json
from pathlib import Path

def sync_all():
    courses_dir = Path("data/courses")
    students_dir = Path("data/students")
    
    for course_path in courses_dir.iterdir():
        if not course_path.is_dir(): continue
        grades_file = course_path / "grades.json"
        if not grades_file.exists(): continue
            
        with open(grades_file, "r") as f:
            grades_data = json.load(f)
            
        records = grades_data.get("records", {})
        for student_id, quizzes in records.items():
            for qnum_str, qdata in quizzes.items():
                if qdata.get("modified"):
                    cfile = students_dir / student_id / course_path.name / f"quiz_{qnum_str}" / "correction.json"
                    if cfile.exists():
                        with open(cfile, "r") as cf:
                            c_data = json.load(cf)
                        
                        if c_data.get("effective_score") != qdata["score"]:
                            c_data["effective_score"] = qdata["score"]
                            with open(cfile, "w") as cf:
                                json.dump(c_data, cf, indent=2)
                            print(f"Updated {cfile} to {qdata['score']}")

if __name__ == "__main__":
    sync_all()
