import os
import json
import google.generativeai as genai
from typing import Dict, Any, Optional
from pathlib import Path
from backend.database import db
import backend.gradebook as gradebook
from datetime import datetime
import re
from backend.config import API_KEY

if API_KEY:
    genai.configure(api_key=API_KEY)

# ... (imports remain)

def identify_scan(scan_path: Path) -> Dict[str, Any]:
    """
    Uses Gemini to identify Student, Course, and Quiz Number from a scan.
    """
    if not api_key:
        return {"error": "No API Key"}

    print(f"DEBUG: identifying scan path: {scan_path}, suffix: {scan_path.suffix}")
    # DEBUG OVERRIDE: If .txt, read directly (Mock OCR)
    if scan_path.suffix == ".txt":
        with open(scan_path, "r") as f:
            content = f.read()
        # Prompt model with text directly
        model = genai.GenerativeModel('gemini-2.0-flash')
        # We wrap it in a prompt to extract JSON
        txt_prompt = f"""
        Extract specific metadata from this text:
        {content}
        
        Output JSON:
        {{
            "student_name": "...",
            "quiz_number": 2,
            "course_title": "..."
        }}
        """
        response = model.generate_content(txt_prompt)
        try:
             text = response.text
             if "```json" in text:
                 text = text.split("```json")[1].split("```")[0]
             elif "```" in text:
                 text = text.split("```")[1].split("```")[0]
             return json.loads(text)
        except:
             return {"error": "Failed to parse text mock"}

    uploaded_file = genai.upload_file(path=scan_path)
    
    prompt = """
    Analyze this document header.
    Extract:
    1. Student Identifier (Look for "Candidate #1234" or "Student: 1234"). The ID is 4 digits.
    2. Quiz Title/Number (e.g. "Quiz #2")
    3. Course Title (e.g. "Math Test")
    
    Output JSON:
    {
        "student_id": "1234",
        "quiz_number": 2,
        "course_title": "..."
    }
    """
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content([prompt, uploaded_file])
    
    try:
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text)
    except Exception as e:
        return {"error": str(e)}

def grade_submission_smart(scan_path: Path, custom_prompt: str = None, include_context: bool = False) -> Dict[str, Any]:
    # 1. Identify
    metadata = identify_scan(scan_path)
    if "error" in metadata:
        raise ValueError(f"Identification failed: {metadata['error']}")
        
    print(f"Identified: {metadata}")
    
    # 2. Resolve IDs
    # Student
    students = db.get_all_students()
    metadata = identify_scan(scan_path)
    if "error" in metadata:
        raise ValueError(f"Identification failed: {metadata['error']}")
        
    print(f"Identified: {metadata}")
    
    # 2. Resolve IDs
    # Student
    students = db.get_all_students()
    
    # NEW: Match by ID
    extracted_id = metadata.get("student_id")
    # If returned as int, convert
    if isinstance(extracted_id, int):
        extracted_id = str(extracted_id)
        
    student = next((s for s in students if s["id"] == extracted_id), None)
    
    # Fallback: Try regex if prompt returned text "Candidate #1234"
    if not student and extracted_id:
        import re
        match = re.search(r'(\d{4})', str(extracted_id))
        if match:
             real_id = match.group(1)
             student = next((s for s in students if s["id"] == real_id), None)
             
    if not student:
        raise ValueError(f"Student ID '{extracted_id}' not found in DB.")
        
    # Course
    courses = db.get_all_courses()
    course_title = metadata.get("course_title", "").lower()
    course = next((c for c in courses if c["title"].lower() in course_title or course_title in c["title"].lower()), None)
    if not course:
        # Fallback: try to match by ID if title is ambiguous
        # Taking the first loose match for now
        raise ValueError(f"Course '{metadata.get('course_title')}' not found in DB.")

    quiz_num = metadata.get("quiz_number")
    if not quiz_num:
         raise ValueError("Quiz number not identified.")

    # 3. Locate Target Quiz Directory
    # data/students/{student_id}/{course_id}/quiz_{number}/
    quiz_dir = Path(f"data/students/{student['id']}/{course['id']}/quiz_{quiz_num}")
    if not quiz_dir.exists():
        # Fallback: Maybe they scan an old quiz before structure change?
        # For this task, we assume new structure.
        raise ValueError(f"Quiz folder not found: {quiz_dir}")
        
    # 4. Move Scan to Folder
    final_scan_path = quiz_dir / f"scan{scan_path.suffix}"
    import shutil
    import time
    shutil.copy(scan_path, final_scan_path)

    # 5. Fetch Context (Subject)
    quizzes = db._read_json(Path("data/global/quizzes.json"))
    original_quiz = next((q for q in quizzes if q["student_id"] == student["id"] 
                          and q["course_id"] == course["id"] 
                          and q.get("quiz_number") == quiz_num), None)
                          
    latex_context = original_quiz["latex_content"] if original_quiz else "Content not found in DB."
    
    # 6. Grade
    # If .txt, read content directly
    # 5b. Inject Course Context if requested
    course_context_injection = ""
    if include_context:
        # heuristic: find largest .tex file in data/courses/{course_id}
        c_dir = Path(f"data/courses/{course['id']}")
        if c_dir.exists():
            tex_files = list(c_dir.glob("*.tex"))
            if tex_files:
                # Pick largest
                main_tex = max(tex_files, key=lambda p: p.stat().st_size)
                try:
                    with open(main_tex, "r") as f:
                        course_context_injection = "Full Course Context (LaTeX Source):\n" + f.read()
                except Exception as e:
                    print(f"Failed to read context: {e}")

    # 6. Grade
    # Construct Base Prompt
    if custom_prompt:
        # If user provides prompt, use it. Handle placeholders if they exist.
        # Fallback to f-string if no placeholders found? No, simple replacement.
        prompt_text = custom_prompt
        # Simple template replacement
        prompt_text = prompt_text.replace("{latex_context}", str(latex_context))
        prompt_text = prompt_text.replace("{course_context_injection}", course_context_injection)
        # Content injection happens below differently for txt vs image
    else:
        prompt_text = f"""
        Role: Strict Grader.
        
        Context:
        Original Questions (LaTeX):
        {latex_context}
        {course_context_injection}
        
        Student Submission (Text/Scan):
        {{student_submission}}
        
        Task:
        1. Transcribe answer if needed.
        2. Grade /20.
        3. Feedback & Weak Points in BILINGUAL FORMAT (English + French).
        
        Output JSON:
        {{
            "transcription": "...",
            "grades": [{{ "question_number": 1, "question_text": "...", "score": 4, "feedback": "Excellent work. \\n\\n Excellent travail." }}],
            "total_score": 15
        }}
        """

    # If .txt, read content directly
    if final_scan_path.suffix == ".txt":
        with open(final_scan_path, "r") as f:
            content = f.read()
            
        final_prompt = prompt_text.replace("{student_submission}", content)
        
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(final_prompt)
    else:
        uploaded_file = genai.upload_file(path=final_scan_path)
        
        # For image, we can't easily replace {student_submission} if it's implicitly the image.
        # So we append the image to the list.
        # And we verify if {student_submission} exists in prompt, replace it with "See attached image".
        final_prompt = prompt_text.replace("{student_submission}", "(See attached image)")
        
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content([final_prompt, uploaded_file])
    
    # Parse
    text = response.text
    try:
        from json_repair import repair_json
        grading_result = json.loads(repair_json(text))
    except Exception as e:
        print(f"ERROR Parsing JSON: {e}")
        print(f"RAW TEXT: {response.text}") # Print original to see what happened
        grading_result = {
            "total_score": 0,
            "grades": [],
            "transcription": "Error parsing AI response",
            "weak_concepts": ["Parsing Error"]
        }
    
    # 7. Save Correction
    correction_path = quiz_dir / "correction.json"
    with open(correction_path, "w") as f:
        json.dump(grading_result, f, indent=2)

    # 8. Record in Gradebook
    # raw_course_id is needed. course['id'] usually.
    # The 'course' dict returned by resolution usually contains 'id'.
    try:
        score_val = float(grading_result.get("total_score", 0))
        gradebook.record_auto_grade(course['id'], student['id'], quiz_num, score_val)
    except Exception as e:
        print(f"Failed to update gradebook: {e}")

    # 9. Update Student History (for future generation)
    try:
        # We store the full correction result
        history_entry = {
            "quiz_number": quiz_num,
            "course_id": course['id'],
            "timestamp": time.time(),
            "correction": grading_result
        }
        db.add_quiz_to_history(student['id'], history_entry)
    except Exception as e:
        print(f"Failed to update student history: {e}")
        
    return {
        "student": f"{student.get('last_name', '')} {student.get('first_name', '')}".strip() or student_id,
        "course": course["title"],
        "raw_course_id": course["id"],
        "quiz": quiz_num,
        "score": grading_result.get("total_score"),
        "path": str(correction_path)
    }

# Keep old function for backward compat if needed, or remove? 
# I will comment it out or leave it be.
def grade_submission_v2(zip_path: Path = None, scan_path: Path = None, student_id: str = None, course_id: str = None) -> Dict[str, Any]:
    # ... Legacy ...
    return {} 

def generate_global_summary(course_id: str, quiz_number: int, custom_prompt: str = None) -> Dict[str, Any]:
    """
    Aggregates all correction.json for a specific quiz and generates a global summary.
    """
    quiz_files = []
    
    # 1. Collect all corrections
    # ... (existing collection logic remains valid, but let's check if I need to see more lines)
    # The snippet view was small. I will assume the collection logic is below line 262 and above 300.
    
    # Let's verify the prompt definition area which I saw in grep
    # It was around line 300.
    
    # We need to construct the aggregated data FIRST (which is likely before line 300)
    # Then define the prompt.
    
    # To be safe, I should read the whole function or at least the part constructing the prompt.
    # The grep showed line 300: summary_prompt = f"""
    
    # Let's read a bit more context to be sure where `compilations` comes from.

    if not api_key:
        return {"error": "No API Key"}
        
    course_dir = Path(f"data/students")
    
    corrections = []
    scores = []
    
    # Iterate all students
    students = db.get_all_students()
    for s in students:
        s_id = s["id"]
        # Path: data/students/{student_id}/{course_id}/quiz_{number}/correction.json
        c_path = course_dir / s_id / course_id / f"quiz_{quiz_number}" / "correction.json"
        
        if c_path.exists():
            try:
                with open(c_path, "r") as f:
                    data = json.load(f)
                    corrections.append(data)
                    if "total_score" in data:
                        scores.append(data["total_score"])
            except:
                pass
    
    if not corrections:
        return {"error": "No corrections found for this quiz."}
        
    avg_score = sum(scores) / len(scores) if scores else 0
    
    # Prepare Context
    all_weak_points = []
    for c in corrections:
        if "weak_concepts" in c:
            all_weak_points.extend(c["weak_concepts"])
            
    if custom_prompt:
        summary_prompt = custom_prompt + f"""
        
        Stats:
        - Count: {len(corrections)} students
        - Average Score: {avg_score:.1f}/20
        
        Common Weak Concepts Reported:
        {", ".join(all_weak_points)}
        """
    else:
        summary_prompt = f"""
        Rôle : Professeur Principal.
        Tâche : Rédiger une courte synthèse globale de la classe basée sur ces résultats.
        
        Statistiques :
        - Nombre : {len(corrections)} étudiants
        - Moyenne : {avg_score:.1f}/20
        
        Concepts mal compris fréquents :
        {", ".join(all_weak_points)}
        
        Format de sortie : Markdown. Soyez encourageant mais précis.
        """
    
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content(summary_prompt)
    summary_text = response.text
    
    # Save Summary
    summary_path = Path(f"data/courses/{course_id}/quiz_{quiz_number}_summary.md")
    # Ensure dir exists (it should)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(summary_path, "w") as f:
        f.write(summary_text)
        
    return {
        "message": "Summary generated",
        "average": avg_score,
        "count": len(corrections),
        "summary": summary_text,
        "path": str(summary_path)
    } 

