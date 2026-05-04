import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

DATA_DIR = Path(__file__).parent.parent / "data"

class Database:
    def __init__(self):
        self.ensure_data_dir()
        
    def ensure_data_dir(self):
        # Create global structure
        (DATA_DIR / "global").mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "courses").mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "students").mkdir(parents=True, exist_ok=True)
        
        # Init global files if missing
        self._init_file(DATA_DIR / "global" / "students.json", [])
        self._init_file(DATA_DIR / "global" / "courses.json", [])
        self._init_file(DATA_DIR / "global" / "quizzes.json", [])

    def _init_file(self, path: Path, default_content: Any):
        if not path.exists():
            with open(path, "w") as f:
                json.dump(default_content, f, indent=2)

    def _read_json(self, path: Path) -> Any:
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _write_json(self, path: Path, data: Any):
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    # --- Global Accessors ---
    def get_all_students(self) -> List[Dict]:
        return self._read_json(DATA_DIR / "global" / "students.json")

    def save_student(self, student: Dict):
        students = self.get_all_students()
        # Update if exists, else append
        for i, s in enumerate(students):
            if s["id"] == student["id"]:
                students[i] = student
                self._write_json(DATA_DIR / "global" / "students.json", students)
                return
        students.append(student)
        self._write_json(DATA_DIR / "global" / "students.json", students)
        # Ensure student dir
        (DATA_DIR / "students" / student["id"]).mkdir(exist_ok=True)
        history_path = DATA_DIR / "students" / student["id"] / "history.json"
        if not history_path.exists():
            self._write_json(history_path, {"weak_concepts": [], "past_quizzes": []})

    def get_all_courses(self) -> List[Dict]:
        return self._read_json(DATA_DIR / "global" / "courses.json")

    def save_course(self, course: Dict):
        courses = self.get_all_courses()
        for i, c in enumerate(courses):
            if c["id"] == course["id"]:
                courses[i] = course
                self._write_json(DATA_DIR / "global" / "courses.json", courses)
                return
        courses.append(course)
        self._write_json(DATA_DIR / "global" / "courses.json", courses)
        # Ensure course dir
        (DATA_DIR / "courses" / course["id"]).mkdir(exist_ok=True)

    # --- Student Specific ---
    def get_student_history(self, student_id: str) -> Dict:
        path = DATA_DIR / "students" / student_id / "history.json"
        if not path.exists():
            return {"weak_concepts": [], "past_quizzes": []}
        return self._read_json(path)

    def add_quiz_to_history(self, student_id: str, quiz_data: Dict):
        path = DATA_DIR / "students" / student_id / "history.json"
        data = self._read_json(path) if path.exists() else {"weak_concepts": [], "past_quizzes": []}

        # Update or Append new quiz
        # Robust comparison (str vs int)
        def normalize(v):
            return str(v).strip().lower()

        target_cid = normalize(quiz_data.get("course_id", ""))
        target_qnum = normalize(quiz_data.get("quiz_number", ""))

        existing_idx = -1
        if "past_quizzes" not in data: 
            data["past_quizzes"] = []
            
        for i, q in enumerate(data["past_quizzes"]):
            q_cid = normalize(q.get("course_id", ""))
            q_qnum = normalize(q.get("quiz_number", ""))
            if q_cid == target_cid and q_qnum == target_qnum:
                existing_idx = i
                break

        if existing_idx >= 0:
            data["past_quizzes"][existing_idx] = quiz_data
        else:
            data["past_quizzes"].append(quiz_data)
        
        # Update weak concepts (Legacy or if we assume we extract them differently)
        # For now, just save.
        self._write_json(path, data)

db = Database()
