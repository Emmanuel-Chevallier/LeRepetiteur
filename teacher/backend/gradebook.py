
import json
import time
from pathlib import Path
from typing import Dict, List, Any

# Ensure we use the same data root logic
DATA_DIR = Path("data")

def _get_gradebook_path(course_id: str) -> Path:
    return DATA_DIR / "courses" / course_id / "grades.json"

def get_gradebook(course_id: str) -> Dict[str, Any]:
    """
    Returns the raw gradebook dictionary.
    Structure:
    {
      "last_updated": float,
      "records": { "student_id": { "quiz_num": { "score": 15, "modified": false, ... } } }
    }
    """
    path = _get_gradebook_path(course_id)
    if not path.exists():
        return {"last_updated": time.time(), "records": {}}
    
    with open(path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"last_updated": time.time(), "records": {}}

def save_gradebook(course_id: str, data: Dict[str, Any]):
    path = _get_gradebook_path(course_id)
    # Ensure dir exists (should be created by course creation, but safe practice)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    data["last_updated"] = time.time()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def record_auto_grade(course_id: str, student_id: str, quiz_number: int, score: float):
    """
    Called by the auto-grader/Gemini. 
    Only updates if not manually modified (or we could decide policy).
    For now, auto-grade overwrites unless 'modified' flag is explicitly True?
    Actually, usually auto-grade is the first step. If I re-run grading, I usually want to update.
    But if I manually fixed it, I might want to keep my fix.
    Let's preserve 'modified' entries.
    """
    gb = get_gradebook(course_id)
    records = gb["records"]
    
    if student_id not in records:
        records[student_id] = {}
        
    quiz_key = str(quiz_number)
    current_entry = records[student_id].get(quiz_key, {})
    
    # If it was manually modified, do we overwrite?
    # User requirement: "modifier ... si je le juge necessaire".
    # If I re-scan, presumably I want the new scan result. 
    # But if I manually edited the *previous* scan result, maybe I want to keep it?
    # Let's say: Auto-grade always overwrites "auto" info, but we should handle the 'modified' flag carefully.
    # Simple logic: Auto-grade acts as a fresh source. We reset 'modified' to False because it's a new machine judgment?
    # OR: If I manually set it to 15, and re-scan, maybe the AI says 12. 
    # I think standard behavior is: Auto-grade = new source of truth.
    
    entry = {
        "score": score,
        "modified": False,
        "timestamp": time.time(),
        "source": "auto"
    }
    
    records[student_id][quiz_key] = entry
    save_gradebook(course_id, gb)

def update_manual_grade(course_id: str, student_id: str, quiz_number: int, new_score: float):
    """
    Called by the UI when teacher edits a cell.
    Sets modified = True.
    """
    gb = get_gradebook(course_id)
    records = gb["records"]
    
    if student_id not in records:
        records[student_id] = {}
        
    quiz_key = str(quiz_number)
    # Check if we had an original score to preserve?
    # Assuming the current stored score was the 'original' or 'previous'.
    # We could store 'original_score' only on the first manual edit.
    
    current_entry = records[student_id].get(quiz_key, {})
    original = current_entry.get("original_score")
    if original is None:
        # The value currently inside 'score' becomes the original
        original = current_entry.get("score")
        
    entry = {
        "score": new_score,
        "modified": True,
        "timestamp": time.time(),
        "source": "manual",
        "original_score": original
    }
    
    records[student_id][quiz_key] = entry
    save_gradebook(course_id, gb)

def get_grade_matrix(course_id: str):
    """
    Helper for UI. Returns list of students and their grades keyed by quiz.
    """
    gb = get_gradebook(course_id)
    records = gb["records"]
    
    # We need to know all available quizzes to build columns.
    # We can scan the records or keep a separate counter.
    # Scanning records is safer.
    all_quizzes = set()
    for s_data in records.values():
        all_quizzes.update(s_data.keys())
        
    sorted_quizzes = sorted([int(q) for q in all_quizzes])
    
    # Build matrix
    matrix = []
    # We might want student names. We can fetch them from `students.json` or rely on ID if not available.
    # It is better to merge with student DB.
    from backend.database import db
    all_students_db = {s["id"]: s for s in db.get_all_students()}
    
    for sid, data in records.items():
        if sid not in all_students_db:
             continue # Skip deleted students
             
        student_obj = all_students_db.get(sid, {})
        s_name = f"{student_obj.get('last_name', '')} {student_obj.get('first_name', '')}".strip() or sid
        row = {
            "student_id": sid,
            "student_name": s_name,
            "grades": {}
        }
        for q_num in sorted_quizzes:
            q_key = str(q_num)
            if q_key in data:
                row["grades"][q_key] = data[q_key]
            else:
                row["grades"][q_key] = None # No grade
        matrix.append(row)
        
    return {
        "quizzes": sorted_quizzes,
        "students": matrix
    }
