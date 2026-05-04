
import os
import sys
import glob
from pathlib import Path

sys.path.append(os.getcwd())
from backend import generator
from backend.database import db

def test_live_generation():
    print("--- Starting Live Generation Test (Student 0001, Course proba) ---")
    
    # Mock db.get_all_students to only return 0001
    original_get_students = db.get_all_students
    db.get_all_students = lambda: [{"id": "0001", "name": "Test Student"}]
    
    try:
        # returns list of dicts: {student_id, quiz_dir, ...}
        results = generator.generate_quizzes_for_course("proba")
        if not results:
             print("❌ No quizzes generated.")
             return
             
        quiz_dir = results[0]["quiz_dir"]
        print(f"✅ Generation completed. Directory: {quiz_dir}")
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        db.get_all_students = original_get_students
        return
    
    db.get_all_students = original_get_students

    # 2. Inspect subject.tex
    subject_tex = Path(quiz_dir) / "subject.tex"
    if not subject_tex.exists():
         print(f"❌ subject.tex not found in {quiz_dir}")
         return
         
    with open(subject_tex, "r") as f:
        content = f.read()
        
    print("\n--- CONTENT SNIPPET ---")
    # Print first 1000 chars of the body (skipping header if possible)
    # usually body is after \begin{document}
    if "\\begin{document}" in content:
        body = content.split("\\begin{document}")[1]
        print(body[:1000])
    else:
        print(content[:1000])
    
    print("\n--- ANALYSIS ---")
    if "\\textit" in content:
         print("✅ Found \\textit{...} (likely French translation).")
    else:
         print("⚠️ No \\textit{...} found. Translation might be missing or formatted differently.")

if __name__ == "__main__":
    test_live_generation()
