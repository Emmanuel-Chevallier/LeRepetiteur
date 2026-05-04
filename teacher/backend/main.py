from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path
import os
import requests
import json
import secrets
import string
import shutil
import csv
import io
from backend.database import db
from backend import generator, grader, gradebook, scan_analyzer
import uuid
import shutil

app = FastAPI()

# Mount Frontend
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Mount Data for Content Serving (Scans)
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
app.mount("/content", StaticFiles(directory=str(DATA_DIR)), name="content")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open(FRONTEND_DIR / "index.html", "r") as f:
        content = f.read()
    return HTMLResponse(content=content, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

# --- Mock Data Init (Remove in Prod) ---
@app.on_event("startup")
async def startup_event():
    # Create Default Teacher/Students if empty
    if not db.get_all_students():
        db.save_student({"id": "student_1", "first_name": "Alice", "last_name": "Student", "role": "student"})
        db.save_student({"id": "student_2", "first_name": "Bob", "last_name": "Student", "role": "student"})

# --- API Endpoints ---
@app.get("/api/students")
def get_students():
    students = db.get_all_students()
    courses = db.get_all_courses()
    
    from backend.gradebook import get_gradebook
    course_gradebooks = {c["id"]: get_gradebook(c["id"]) for c in courses}
    
    for s in students:
        sid = s.get("id")
        absences = 0
        total_score = 0.0
        score_count = 0
        
        course_stats = {}
        for c in courses:
            c_id = c["id"]
            attendance_records = c.get("attendance", {}).get("records", {}).get(sid, {})
            c_abs = sum(1 for status in attendance_records.values() if status == "absent")
            absences += c_abs
            
            gb = course_gradebooks.get(c_id, {})
            student_grades = gb.get("records", {}).get(sid, {})
            
            c_total = 0.0
            c_count = 0
            for q_data in student_grades.values():
                score = q_data.get("score")
                if score is not None:
                    try:
                        val = float(score)
                        total_score += val
                        score_count += 1
                        c_total += val
                        c_count += 1
                    except ValueError:
                        pass
            
            course_stats[c_id] = {
                "absences": c_abs,
                "average_grade": round(c_total / c_count, 2) if c_count > 0 else "-"
            }
        
        s["absences"] = absences
        if score_count > 0:
            s["average_grade"] = round(total_score / score_count, 2)
        else:
            s["average_grade"] = "-"
            
        s["course_stats"] = course_stats

    # Sort students by id string (e.g. "0001", "0002")
    return sorted(students, key=lambda s: s.get("id", ""))

@app.post("/api/students")
async def add_student(payload: dict):
    # payload: {"id": "1234"}
    sid = payload.get("id")
    if not sid:
        raise HTTPException(status_code=400, detail="ID required")
    
    # Validation: 4 digits
    if not sid.isdigit() or len(sid) != 4:
        raise HTTPException(status_code=400, detail="ID must be exactly 4 digits.")
        
    # Check duplicate
    if next((s for s in db.get_all_students() if s["id"] == sid), None):
        raise HTTPException(status_code=400, detail="Student ID already exists")
        
    # Anonymized: Name = ID or "Student {ID}"?
    # User said: "anonymisé et identifié par simple numéro".
    # Implementation Plan: "name": "student_1234" (internal) but check implementation.
    # Let's settle on name="student_{id}" for internal consistency, or just "{id}".
    # "Le logiciel ne verra jamais leur nom."
    # Let's set name = "Candidate #" + sid to be printable directly?
    # Or just keep it as the ID string.
    
    student = {
        "id": sid,
        "role": "student"
    }
    db.save_student(student)
    db.save_student(student)
    return {"message": "Student added", "student": student}

def _get_next_student_id():
    existing_students = db.get_all_students()
    existing_ids = [int(s["id"]) for s in existing_students if s["id"].isdigit()]
    return max(existing_ids) + 1 if existing_ids else 1

class EditStudentRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None

@app.patch("/api/students/{student_id}")
async def edit_student(student_id: str, payload: EditStudentRequest):
    students = db.get_all_students()
    student = next((s for s in students if s["id"] == student_id), None)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    if payload.first_name is not None:
        student["first_name"] = payload.first_name
    if payload.last_name is not None:
        student["last_name"] = payload.last_name
    if payload.email is not None:
        student["email"] = payload.email
    elif "email" in (payload.__fields_set__ if hasattr(payload, '__fields_set__') else set()):
        student["email"] = None
        
    db.save_student(student)
    return {"message": "Student updated", "student": student}

@app.post("/api/students/import_csv")
async def import_students_csv(file: UploadFile = File(...)):
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Cannot decode CSV file: {e}")
            
    csv_file = io.StringIO(text)
    
    delimiters = [';', ',', '\t']
    best_delimiter = ';'
    
    for d in delimiters:
        csv_file.seek(0)
        reader = csv.DictReader(csv_file, delimiter=d)
        if reader.fieldnames and len(reader.fieldnames) > 1:
            best_delimiter = d
            best_fieldnames = [f.lower().strip() for f in reader.fieldnames]
            if any("nom" in f for f in best_fieldnames):
                break
                
    csv_file.seek(0)
    reader = csv.DictReader(csv_file, delimiter=best_delimiter)
    
    first_name_col = None
    last_name_col = None
    
    if reader.fieldnames:
        for f in reader.fieldnames:
            fl = f.lower().strip()
            if "prénom" in fl or "prenom" in fl or "first" in fl:
                first_name_col = f
            elif "nom" in fl or "last" in fl:
                if not first_name_col or ("prénom" not in fl and "prenom" not in fl):
                    last_name_col = f
                    
    if not last_name_col:
        if reader.fieldnames and len(reader.fieldnames) >= 2:
            last_name_col = reader.fieldnames[0]
            first_name_col = reader.fieldnames[1]
        else:
            raise HTTPException(status_code=400, detail="CSV must have at least 'Nom' and 'Prénom' columns.")
            
    next_id = _get_next_student_id()
    imported_count = 0
    
    # Get existing students to check for duplicates
    existing_students = db.get_all_students()
    
    # Track name occurrences to append (2), (3)...
    name_counts = {}
    for s in existing_students:
        # Create a lowercase key to accurately count case-insensitive matches
        ln = (s.get("last_name") or "").strip().lower()
        fn = (s.get("first_name") or "").strip().lower()
        if ln or fn:
            # The base key without any existing (2) suffix
            # E.g. "curie (2)" -> we just want "curie" for counting, though it's simpler to just count exact matches
            # Actually, to make it simple we count exact matches of the base name.
            import re
            
            # Remove any trailing " (number)"
            base_ln = re.sub(r'\s*\(\d+\)$', '', s.get("last_name") or "").strip().lower()
            key = f"{base_ln}_{fn}"
            name_counts[key] = name_counts.get(key, 0) + 1
    
    for row in reader:
        last_name = row.get(last_name_col, "").strip()
        first_name = row.get(first_name_col, "").strip()
        
        if not last_name and not first_name:
            continue
            
        # Duplicate check logic
        base_ln_lower = last_name.lower()
        fn_lower = first_name.lower()
        key = f"{base_ln_lower}_{fn_lower}"
        
        if key in name_counts:
            # It already exists, we must append a suffix
            name_counts[key] += 1
            suffix = f" ({name_counts[key]})"
            last_name = f"{last_name}{suffix}"
        else:
            name_counts[key] = 1
            
        sid = str(next_id).zfill(4)
        next_id += 1
        
        student = {
            "id": sid,
            "first_name": first_name,
            "last_name": last_name,
            "role": "student",
            "password": generate_password()
        }
        db.save_student(student)
        imported_count += 1
        
    return {"message": "Import successful", "imported_count": imported_count}

@app.post("/api/students/batch")
async def add_students_batch(payload: dict):
    # payload: {"start_id": 2000, "count": 30}
    start_id = int(payload.get("start_id", 0))
    count = int(payload.get("count", 0))

    if start_id <= 0 or count <= 0:
        raise HTTPException(status_code=400, detail="Start ID and Count must be positive.")
        
    created = 0
    skipped = 0
    existing_students = {s["id"] for s in db.get_all_students()}
    
    for i in range(count):
        current_num = start_id + i
        sid = str(current_num).zfill(4)
        
        if len(sid) != 4:
            # Skip if ID exceeds 4 digits (e.g. 10000)
            skipped += 1
            continue
            
        if sid in existing_students:
            skipped += 1
            continue
            
        student = {
            "id": sid,
            "role": "student"
        }
        db.save_student(student)
        created += 1
        
    return {"message": "Batch complete", "created": created, "skipped": skipped}

@app.delete("/api/students/{student_id}")
async def delete_student(student_id: str):
    # 1. Remove from global Student List
    students = db.get_all_students()
    new_list = [s for s in students if s["id"] != student_id]
    
    if len(new_list) == len(students):
        raise HTTPException(status_code=404, detail="Student not found")
        
    db._write_json(Path("data/global/students.json"), new_list)
    
    # 2. Cleanup from Courses (Enrolled Lists) and Course Data
    courses = db.get_all_courses()
    for c in courses:
        cid = c["id"]
        # Remove from enrolled list
        if "enrolled_students" in c and student_id in c["enrolled_students"]:
            c["enrolled_students"].remove(student_id)
            db.save_course(c)
            
        # Cleanup Student Data in Course (if any specific data exists here)
        # Structure: data/courses/{course_id}/students/{student_id} ?
        # Or maybe quizzes are checked elsewhere.
        # Let's try to remove data/courses/{cid}/students/{student_id}
        course_student_dir = Path(f"data/courses/{cid}/students/{student_id}")
        if course_student_dir.exists():
             try:
                 shutil.rmtree(course_student_dir)
             except Exception as e:
                 print(f"Warning: Could not remove {course_student_dir}: {e}")

    # 3. Cleanup Global Student Data (scans, history?)
    # Structure: data/students/{student_id}
    global_student_dir = Path(f"data/students/{student_id}")
    if global_student_dir.exists():
        try:
            shutil.rmtree(global_student_dir)
        except Exception as e:
             print(f"Warning: Could not remove {global_student_dir}: {e}")
            
    return {"message": "Student deleted (Files & Data purged)"}

def generate_password(length=6):
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

@app.post("/api/students/passwords/generate")
async def generate_student_passwords():
    students = db.get_all_students()
    updated_count = 0
    for s in students:
        if "password" not in s or not s["password"]:
            s["password"] = generate_password()
            updated_count += 1
            # We need to save each student. Since save_student loads all students, 
            # calling it in a loop is inefficient (O(N^2) IO).
            # Better to update the list and save once.
    
    # Batch Save logic
    if updated_count > 0:
        db._write_json(Path("data/global/students.json"), students)
        
    return {"message": f"Generated passwords for {updated_count} students.", "students": students}

@app.get("/api/courses")
def get_courses():
    return db.get_all_courses()

# --- Course Management ---

@app.post("/api/courses")
async def create_course(payload: dict):
    # Payload: {"name": "Math 101"}
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Name required")
    
    # Auto-generate simplified ID
    course_id = name.lower().replace(" ", "_").replace("-", "_")
    
    # Check duplicate
    if next((c for c in db.get_all_courses() if c["id"] == course_id), None):
         raise HTTPException(status_code=400, detail="Course already exists")

    course = {
        "id": course_id,
        "title": name,
        "latex_file_path": "",
        "last_covered_line": 0,
        "custom_prompt": "",
        "enrolled_students": [] 
    }
    db.save_course(course)
    return {"message": "Course created", "course": course}

@app.post("/api/courses/{course_id}/enrollments")
async def update_enrollments(course_id: str, payload: dict):
    # Payload: {"student_ids": ["s1", "s2"]}
    courses = db.get_all_courses()
    course = next((c for c in courses if c["id"] == course_id), None)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    course["enrolled_students"] = payload.get("student_ids", [])
    db.save_course(course)
    return {"message": "Enrollments updated", "enrolled": course["enrolled_students"]}

from fastapi import File, UploadFile
import shutil

@app.post("/api/courses/{course_id}/upload")
async def upload_course_source(course_id: str, file: UploadFile = File(...)):
    # 1. Save File
    course_dir = Path(f"data/courses/{course_id}")
    course_dir.mkdir(parents=True, exist_ok=True)
    file_path = course_dir / file.filename
    
    with open(file_path, "wb+") as f:
        shutil.copyfileobj(file.file, f)
        
    # 2. Update DB
    courses = db.get_all_courses()
    course = next((c for c in courses if c["id"] == course_id), None)
    if course:
        course["latex_file_path"] = str(file_path)
        db.save_course(course)
        
    return {"message": "File uploaded", "path": str(file_path)}

@app.get("/api/courses/{course_id}/source")
async def get_course_source(course_id: str):
    courses = db.get_all_courses()
    course = next((c for c in courses if c["id"] == course_id), None)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    latex_path_str = course.get("latex_file_path", "")
    if not latex_path_str:
        raise HTTPException(status_code=404, detail="No source file uploaded")
         
    latex_path = Path(latex_path_str)
    if not latex_path.exists():
        raise HTTPException(status_code=404, detail="Source file not found on disk")
         
    try:
        content = latex_path.read_text(encoding="utf-8", errors="replace")
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/courses/{course_id}/settings")
async def update_course_settings(course_id: str, payload: dict):
    # Payload: {"last_covered_line": 50, "custom_prompt": "..."}
    courses = db.get_all_courses()
    course = next((c for c in courses if c["id"] == course_id), None)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    if "start_line" in payload:
        course["start_line"] = int(payload["start_line"]) if payload["start_line"] else 0
    if "end_line" in payload:
        course["end_line"] = int(payload["end_line"]) if payload["end_line"] else None
    if "custom_prompt" in payload:
        course["custom_prompt"] = payload["custom_prompt"]

    if "custom_grading_prompt" in payload:
        course["custom_grading_prompt"] = payload["custom_grading_prompt"]

    if "custom_summary_prompt" in payload:
        course["custom_summary_prompt"] = payload["custom_summary_prompt"]
        
    db.save_course(course)
    return {"message": "Settings updated", "course": course}

@app.get("/api/courses/{course_id}/preview")
async def preview_content(course_id: str):
    courses = db.get_all_courses()
    course = next((c for c in courses if c["id"] == course_id), None)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    latex_path_str = course.get("latex_file_path", "")
    if not latex_path_str:
        return {"preview": "Aucun fichier source téléversé.", "total_lines": 0}
        
    latex_path = Path(latex_path_str)
    if not latex_path.exists():
        return {"preview": "Fichier introuvable sur le disque.", "total_lines": 0}
        
    try:
        with open(latex_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            
        total_lines = len(lines)
        start_line = course.get("start_line", 0)
        end_line = course.get("end_line")
        if end_line is None or end_line > total_lines:
            end_line = total_lines
            
        # Extract slices
        slice_lines = lines[start_line:end_line]
        
        if not slice_lines:
            return {"preview": "Intervalle vide.", "total_lines": total_lines}
            
        # Construct simplified preview with LINE NUMBERS
        # Note: We display 1-based line numbers for user convenience, matching text editors.
        # But we reflect the ACTUAL lines being selected by the current 0-based index settings.
        preview_text = ""
        head = slice_lines[:5]
        
        for i, line in enumerate(head):
            # Calculate actual line number in file (1-based for display)
            # start_line is 0-based index. 
            # If start_line=0, we are reading line index 0. Display "Line 1".
            actual_num = start_line + i + 1
            preview_text += f"Ligne {actual_num}: {line}"

        if len(slice_lines) > 10:
             skips = len(slice_lines) - 10
             preview_text += f"\n... [ {skips} lignes masquées ] ...\n\n"
             
        tail = slice_lines[-5:] if len(slice_lines) > 5 else []
        tail_start_idx = len(slice_lines) - len(tail)
        
        for i, line in enumerate(tail):
            # internal index relative to slice start
            actual_num = start_line + tail_start_idx + i + 1
            preview_text += f"Ligne {actual_num}: {line}"
            
        return {
            "preview": preview_text,
            "total_lines": total_lines,
            "interval_count": len(slice_lines),
            "start": start_line,
            "end": end_line
        }
    except Exception as e:
        return {"preview": f"Erreur de lecture: {str(e)}", "total_lines": 0}

@app.delete("/api/courses/{course_id}")
async def delete_course(course_id: str):
    # 1. Remove from DB
    courses = db.get_all_courses()
    new_courses = [c for c in courses if c["id"] != course_id]
    
    if len(new_courses) == len(courses):
        raise HTTPException(status_code=404, detail="Course not found")
        
    db._write_json(Path("data/global/courses.json"), new_courses)
    
    # 2. Cleanup Data Directory
    course_dir = Path(f"data/courses/{course_id}")
    if course_dir.exists():
        try:
            shutil.rmtree(course_dir)
        except Exception as e:
            print(f"Warning: Could not delete dir {course_dir}: {e}")
            
    return {"message": "Course deleted"}

from backend.generator import generate_quizzes_for_course, generate_quiz_for_student

from fastapi.responses import StreamingResponse
import json

@app.post("/api/courses/{course_id}/generate")
async def generate_quizzes(course_id: str, payload: dict = Body(None)):
    try:
        # Update settings if provided
        if payload and "custom_prompt" in payload and payload["custom_prompt"]:
             courses = db.get_all_courses()
             course = next((c for c in courses if c["id"] == course_id), None)
             if course:
                 course["custom_prompt"] = payload["custom_prompt"]
                 db.save_course(course)
             
        regenerate = payload.get("regenerate", False) if payload else False
        specific_instructions = payload.get("specific_instructions") if payload else None
        selected_questions = payload.get("selected_questions", "") if payload else ""
        n_new = int(payload.get("n_new", 0)) if payload else 0
        n_old = int(payload.get("n_old", 0)) if payload else 0
        
        def iter_generation():
            gen = generate_quizzes_for_course(
                course_id, 
                regenerate=regenerate, 
                specific_instructions=specific_instructions,
                selected_questions=selected_questions,
                n_new=n_new,
                n_old=n_old
            )
            for event in gen:
                yield json.dumps(event) + "\n"
        
        return StreamingResponse(iter_generation(), media_type="application/x-ndjson")
        
    except Exception as e:
        print(f"Generation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/courses/{course_id}/generate_single")
async def generate_single_quiz_endpoint(course_id: str, payload: dict = Body(...)):
    """Generate/regenerate a quiz for a single student."""
    try:
        student_id = payload.get("student_id")
        quiz_number = payload.get("quiz_number")
        specific_instructions = payload.get("specific_instructions")
        custom_prompt = payload.get("custom_prompt")
        context_source = payload.get("context_source", "current")
        selected_questions = payload.get("selected_questions", "")
        n_new = int(payload.get("n_new", 0))
        n_old = int(payload.get("n_old", 0))
        
        if not student_id or quiz_number is None:
            raise HTTPException(status_code=400, detail="student_id and quiz_number are required")
        
        quiz_number = int(quiz_number)
        
        # Update custom prompt if provided
        if custom_prompt:
            courses = db.get_all_courses()
            course = next((c for c in courses if c["id"] == course_id), None)
            if course:
                course["custom_prompt"] = custom_prompt
                db.save_course(course)
        
        def iter_generation():
            gen = generate_quiz_for_student(
                course_id, 
                student_id, 
                quiz_number, 
                specific_instructions=specific_instructions, 
                context_source=context_source,
                selected_questions=selected_questions,
                n_new=n_new,
                n_old=n_old
            )
            for event in gen:
                yield json.dumps(event) + "\n"
        
        return StreamingResponse(iter_generation(), media_type="application/x-ndjson")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Individual Generation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/courses/{course_id}/quiz_bank/{quiz_number}")
async def get_quiz_bank(course_id: str, quiz_number: int):
    """Retrieve the saved question bank for a specific quiz."""
    bank_path = Path(f"data/courses/{course_id}/quiz_{quiz_number}_selected_bank.json")
    if not bank_path.exists():
        raise HTTPException(status_code=404, detail=f"Aucune banque de questions sauvegardée pour le quiz {quiz_number}")
    return db._read_json(bank_path)

from backend.generator import generate_question_bank

@app.post("/api/courses/{course_id}/generate_bank")
async def api_generate_question_bank(course_id: str, payload: dict = Body(...)):
    try:
        prompt = payload.get("prompt")
        num_questions = int(payload.get("num_questions", 10))
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")
        questions = generate_question_bank(course_id, prompt, num_questions)
        return {"questions": questions}
    except Exception as e:
        print(f"Bank Generation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/courses/{course_id}/question_bank")
async def api_save_question_bank(course_id: str, payload: dict = Body(...)):
    try:
        new_questions = payload.get("questions", [])
        if not new_questions:
            return {"message": "No questions to save"}
            
        bank_path = Path(f"data/courses/{course_id}/question_bank.json")
        bank_path.parent.mkdir(parents=True, exist_ok=True)
        
        existing_bank = []
        if bank_path.exists():
            with open(bank_path, "r", encoding="utf-8") as f:
                existing_bank = json.load(f)
                
        # Append new questions
        for q_text in new_questions:
            existing_bank.append({
                "id": str(uuid.uuid4()),
                "text": q_text
            })
            
        with open(bank_path, "w", encoding="utf-8") as f:
            json.dump(existing_bank, f, indent=2, ensure_ascii=False)
            
        return {"message": "Questions saved successfully", "total_questions": len(existing_bank)}
    except Exception as e:
        print(f"Save Bank Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from backend.grader import grade_submission_v2

@app.post("/api/grading/upload")
async def upload_grading(student_id: str, course_id: str, file: UploadFile = File(...)):
    # 1. Save Scan
    student_dir = Path(f"data/students/{student_id}")
    student_dir.mkdir(parents=True, exist_ok=True)
    scan_path = student_dir / f"scan_{course_id}_{file.filename}"
    
    with open(scan_path, "wb+") as f:
        shutil.copyfileobj(file.file, f)
        
    # 2. Grade
    try:
        result = grade_submission_v2(scan_path=scan_path, student_id=student_id, course_id=course_id)
        return {"message": "Grading Complete", "result": result}
    except Exception as e:
        print(f"Grading Error: {e}")
        return {"message": "Grading Failed", "error": str(e)}

from backend.grader import grade_submission_smart

@app.post("/api/grading/smart")
async def smart_grading(
    file: UploadFile = File(...),
    custom_prompt: Optional[str] = Form(None),
    include_context: bool = Form(False),
    is_bulk: bool = Form(False),
    override_quiz_number: Optional[int] = Form(None),
    override_course_id: Optional[str] = Form(None),
    pages_per_copy: int = Form(1)
):
    # 1. Save Temp
    temp_dir = Path("data/temp")
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / file.filename
    print(f"DEBUG: Saved temp file to {temp_path} (name={file.filename})")
    
    with open(temp_path, "wb+") as f:
        shutil.copyfileobj(file.file, f)
        
    # 2. Bulk Processing
    if is_bulk:
        import pypdf
        reader = pypdf.PdfReader(temp_path)
        count = len(reader.pages)
        
        async def iter_bulk():
            results = []
            try:
                total_pages = len(reader.pages)
                step = pages_per_copy
                
                # Iterate by chunks
                for i in range(0, total_pages, step):
                    chunk_index = (i // step) + 1
                    total_chunks = (total_pages + step - 1) // step
                    
                    # Progress Event
                    yield json.dumps({
                        "type": "progress",
                        "current": chunk_index,
                        "total": total_chunks,
                        "message": f"Processing Copy {chunk_index}/{total_chunks} (Pages {i+1}-{min(i+step, total_pages)})..."
                    }) + "\n"
                    
                    # Split logic (Chunk)
                    page_filename = f"{temp_path.stem}_copy_{chunk_index}.pdf"
                    page_path = temp_dir / page_filename
                    writer = pypdf.PdfWriter()
                    
                    # Add all pages in this chunk
                    for j in range(i, min(i + step, total_pages)):
                        writer.add_page(reader.pages[j])
                        
                    with open(page_path, "wb") as f_out:
                         writer.write(f_out)
                         
                    # Grade
                    try:
                        # WRAP SYNC CALL IN THREADPOOL to avoid blocking event loop
                        from fastapi.concurrency import run_in_threadpool
                        res = await run_in_threadpool(
                            grade_submission_smart, 
                            page_path, 
                            custom_prompt=custom_prompt, 
                            include_context=include_context,
                            override_quiz_number=override_quiz_number,
                            override_course_id=override_course_id
                        )
                        results.append(res)
                    except Exception as e:
                        print(f"Error processing page {i+1}: {e}")
                        results.append({"error": f"Page {i+1}: {str(e)}"})
                
                # Final Event
                yield json.dumps({
                    "type": "result",
                    "results": results,
                    "message": f"Bulk Grading Complete ({count} pages)"
                }) + "\n"
                
            except Exception as e:
                yield json.dumps({"type": "error", "error": str(e)}) + "\n"

        return StreamingResponse(iter_bulk(), media_type="application/x-ndjson")

    # 3. Smart Grade (Single)
    try:
        result = grade_submission_smart(
            temp_path, 
            custom_prompt=custom_prompt, 
            include_context=include_context,
            override_quiz_number=override_quiz_number,
            override_course_id=override_course_id
        )
        # Cleanup temp? Maybe keep for debug?
        return {"message": "Smart Grading Complete", "result": result}
    except Exception as e:
        print(f"Smart Grading Error: {e}")
        return {"message": "Smart Grading Failed", "error": str(e)}

# --- Smart Scan V2 Endpoints ---

@app.post("/api/analyze_scan")
async def analyze_scan_endpoint(
    file: UploadFile = File(...), 
    pages_per_copy: int = Form(2),
    default_quiz_number: Optional[int] = Form(None)
):
    """
    Step 1: Upload and Analyze Header (Supports Bulk Split)
    """
    try:
        # Save to temp
        temp_dir = DATA_DIR / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        file_id = str(uuid.uuid4())
        ext = Path(file.filename).suffix
        temp_path = temp_dir / f"{file_id}{ext}"
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Analyze (with split)
        # Returns List[Dict]
        results = scan_analyzer.analyze_header(temp_path, pages_per_copy=pages_per_copy, default_quiz_number=default_quiz_number)
        
        return {
            "original_filename": file.filename,
            "results": results
        }
    except Exception as e:
        print(f"Analyze Scan Error: {e}")
        return {"error": str(e)}

@app.post("/api/scan/split")
async def split_scan_endpoint(
    file: UploadFile = File(...), 
    pages_per_copy: int = Form(2)
):
    try:
        temp_dir = DATA_DIR / "temp"
        temp_dir.mkdir(exist_ok=True)
        file_id = str(uuid.uuid4())
        ext = Path(file.filename).suffix
        temp_path = temp_dir / f"{file_id}{ext}"
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        chunks = scan_analyzer.split_pdf(temp_path, pages_per_copy)
        # Return path relative to temp or just names? 
        # Chunks are in 'temp/chunks/file_id/...'
        # We need to return info so frontend can ask for them back.
        # Let's return the relative path from DATA_DIR
        
        chunk_info = []
        for c in chunks:
            # c is absolute. 
            # rel to DATA_DIR
            rel_path = str(c.relative_to(DATA_DIR))
            chunk_info.append({"path": rel_path, "name": c.name})
            
        return {"message": "Split success", "chunks": chunk_info}
    except Exception as e:
        print(f"Split Scan Error: {e}")
        return {"error": str(e)}

@app.post("/api/scan/analyze_chunk")
async def analyze_chunk_endpoint(
    chunk_path: str = Form(...),
    default_quiz_number: Optional[int] = Form(None)
):
    try:
        # chunk_path is relative to DATA_DIR
        full_path = DATA_DIR / chunk_path
        if not full_path.exists():
            print(f"Analyze Chunk Error: Chunk not found at {full_path}")
            return {"error": "Chunk not found"}
            
        result = scan_analyzer.analyze_single_chunk(full_path, default_quiz_number=default_quiz_number)
        return {"result": result}
    except Exception as e:
        print(f"Analyze Chunk Error: {e}")
        return {"error": str(e)}

class VerifiedGradeRequest(BaseModel):
    file_id: str
    student_id: str
    quiz_number: int
    course_id: str
    custom_prompt: Optional[str] = None

@app.post("/api/grade_scan_verified")
async def grade_scan_verified_endpoint(payload: VerifiedGradeRequest):
    """
    Step 2: Grade with Verified Metadata
    """
    try:
        temp_dir = DATA_DIR / "temp"
        # Find file with this ID (ignore extension knowledge if possible, or assume pdf/img)
        # We stored it as {file_id}{ext} or chunks like {file_id}_part_1{ext}
        # In frontend, item.file_id is the chunk name (e.g., DOC250226-25022026172059_part_1.pdf)
        # So we can just check if it exists in temp or chunks directly
        
        # Try finding the exact file name first
        found_file = next(temp_dir.rglob(payload.file_id), None)
        if not found_file:
            # Fallback to prefix matching just in case
            found_file = next(temp_dir.rglob(f"{payload.file_id}.*"), None)
            
        if not found_file:
            # Debug: print files in temp
            print(f"DEBUG: Files in temp: {list(temp_dir.rglob('*'))}")
            raise HTTPException(status_code=404, detail=f"Temp file {payload.file_id} not found or expired.")
            
        # Call Grader with overrides
        # Grader handles moving the file to final destination
        result = grader.grade_submission_smart(
            scan_path=found_file,
            custom_prompt=payload.custom_prompt,
            include_context=True, # Default to true for V2? Or optional? User said "concatener pdf test", implying context.
            override_quiz_number=payload.quiz_number,
            override_course_id=payload.course_id,
            override_student_id=payload.student_id
        )
        
        # Cleanup temp
        # found_file.unlink() # Grader copies it. safe to delete?
        # grader.py says: shutil.copy(scan_path, final_scan_path). So yes.
        try:
             found_file.unlink()
        except:
             pass
             
        return {"message": "Grading Complete", "result": result}
        
    except Exception as e:
        print(f"Verified Grading Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SummaryRequest(BaseModel):
    custom_prompt: str = None

@app.post("/api/courses/{course_id}/quizzes/{quiz_number}/summary")
async def create_quiz_summary(course_id: str, quiz_number: int, req: SummaryRequest = None):
    try:
        prompt = req.custom_prompt if req else None
        report = grader.generate_global_summary(course_id, quiz_number, prompt)
        return report
    except Exception as e:
        print(f"Error generating summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Gradebook Endpoints
@app.get("/api/courses/{course_id}/grades")
async def get_course_grades(course_id: str):
    return gradebook.get_grade_matrix(course_id)

class GradeUpdate(BaseModel):
    student_id: str
    quiz_number: int
    score: float

@app.post("/api/courses/{course_id}/grades")
async def update_grade(course_id: str, payload: GradeUpdate):
    gradebook.update_manual_grade(course_id, payload.student_id, payload.quiz_number, payload.score)
    
    # Update correction.json and history.json
    quiz_dir = Path(f"data/students/{payload.student_id}/{course_id}/quiz_{payload.quiz_number}")
    correction_path = quiz_dir / "correction.json"
    if correction_path.exists():
        import json
        with open(correction_path, "r") as f:
            correction = json.load(f)
        
        print("UPDATING CORRECTION JSON", correction_path)
        correction["effective_score"] = payload.score
        
        with open(correction_path, "w") as f:
            json.dump(correction, f, indent=2)
            
        # Update history.json
        import time
        history_entry = {
            "quiz_number": payload.quiz_number,
            "course_id": course_id,
            "timestamp": time.time(),
            "correction": correction
        }
        db.add_quiz_to_history(payload.student_id, history_entry)
        
    return {"status": "ok"}

# Attendance Endpoints
class AttendanceSession(BaseModel):
    date: str
    time: str

@app.get("/api/courses/{course_id}/attendance")
async def get_attendance(course_id: str):
    courses = db.get_all_courses()
    course = next((c for c in courses if c["id"] == course_id), None)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    attendance = course.get("attendance", {"sessions": [], "records": {}})
    return attendance

@app.post("/api/courses/{course_id}/attendance/session")
async def add_attendance_session(course_id: str, payload: AttendanceSession):
    courses = db.get_all_courses()
    course = next((c for c in courses if c["id"] == course_id), None)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    session_id = f"{payload.date}_{payload.time}"
    # Initialize attendance if it doesn't exist
    if "attendance" not in course:
        course["attendance"] = {"sessions": [], "records": {}}
    attendance = course["attendance"]
    
    # Avoid duplicate session
    if any(s["id"] == session_id for s in attendance["sessions"]):
        raise HTTPException(status_code=400, detail="Session already exists")
        
    attendance["sessions"].append({
        "id": session_id,
        "date": payload.date,
        "time": payload.time
    })
    
    # Sort sessions chronologically
    attendance["sessions"].sort(key=lambda s: (s["date"], s["time"]))
    
    db.save_course(course)
    return {"message": "Session added", "attendance": attendance}

@app.delete("/api/courses/{course_id}/attendance/session/{session_id}")
async def delete_attendance_session(course_id: str, session_id: str):
    courses = db.get_all_courses()
    course = next((c for c in courses if c["id"] == course_id), None)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    if "attendance" not in course:
        raise HTTPException(status_code=404, detail="No attendance data found")
        
    attendance = course["attendance"]
    
    initial_len = len(attendance["sessions"])
    attendance["sessions"] = [s for s in attendance["sessions"] if s["id"] != session_id]
    
    if len(attendance["sessions"]) == initial_len:
        raise HTTPException(status_code=404, detail="Session not found")
        
    for student_id in attendance.get("records", {}):
        attendance["records"][student_id].pop(session_id, None)
        
    db.save_course(course)
    return {"message": "Session deleted"}

class AttendanceRecord(BaseModel):
    student_id: str
    session_id: str
    status: str  # "présent", "excusé", "absent"

@app.post("/api/courses/{course_id}/attendance/record")
async def update_attendance_record(course_id: str, payload: AttendanceRecord):
    courses = db.get_all_courses()
    course = next((c for c in courses if c["id"] == course_id), None)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    if "attendance" not in course:
        course["attendance"] = {"sessions": [], "records": {}}
    attendance = course["attendance"]
    
    if payload.student_id not in attendance["records"]:
        attendance["records"][payload.student_id] = {}
        
    attendance["records"][payload.student_id][payload.session_id] = payload.status
    
    db.save_course(course)
    return {"message": "Record updated"}

from backend.chatbot import get_chat_response
from pydantic import BaseModel
from typing import List, Dict

class ChatRequest(BaseModel):
    student_id: str
    course_id: str = None # Optional context
    message: str
    history: List[Dict[str, str]] = []

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    return StreamingResponse(
        get_chat_response(req.student_id, req.message, req.history, req.course_id),
        media_type="text/plain"
    )

import json




import zipfile
import io
import requests


from backend.sync_utils import generate_manifest
import json

class DeployRequest(BaseModel):
    mode: str = "smart" # 'smart' or 'full'

@app.post("/api/deploy")
async def deploy_to_student_app(req: DeployRequest = None):
    """
    Deploys data to Student App.
    Mode 'full': Zips everything, wipes student data.
    Mode 'smart': Computes diff, sends only changes and deletions.
    """
    STUDENT_APP_URL = "http://localhost:8001/api/sync"
    MANIFEST_URL = "http://localhost:8001/api/sync/manifest"
    
    # Default to smart if not specified
    mode = req.mode if req else "smart"

    # --- SFTP MODE (University Server) ---
    if mode == "sftp":
        import subprocess
        import sys
        
        script_path = Path(__file__).parent.parent / "sftp_deploy.py"
        if not script_path.exists():
            raise HTTPException(status_code=500, detail=f"Script not found at {script_path}")

        def iter_sftp():
            try:
                process = subprocess.Popen(
                    [sys.executable, "-u", str(script_path)], # -u for unbuffered
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
                for line in process.stdout:
                    yield line
                
                process.wait()
                if process.returncode != 0:
                    yield f"\n[ERROR] Sync exited with code {process.returncode}"
            except Exception as e:
                yield f"\n[EXCEPTION] {e}"

        return StreamingResponse(iter_sftp(), media_type="text/plain")

    
    try:
        files_to_upload = [] # List of Path objects
        files_to_delete = [] # List of relative path strings
        
        # --- 1. DETERMINE DIFF ---
        if mode == "smart":
            try:
                # Fetch Manifest
                resp = requests.get(MANIFEST_URL)
                if resp.status_code != 200:
                    print("Manifest fetch failed, falling back to full.")
                    mode = "full"
                else:
                    student_manifest = resp.json()
                    local_manifest = generate_manifest(DATA_DIR)
                    
                    # A. Uploads (Local has it, Student doesn't OR Hash mismatch)
                    for rel_path, local_hash in local_manifest.items():
                        if rel_path not in student_manifest or student_manifest[rel_path] != local_hash:
                            files_to_upload.append(DATA_DIR / rel_path)
                            
                    # B. Deletions (Student has it, Local doesn't)
                    for rel_path in student_manifest:
                        if rel_path not in local_manifest:
                            files_to_delete.append(rel_path)
                            
                    print(f"Smart Sync: {len(files_to_upload)} updates, {len(files_to_delete)} deletions.")
                    
                    if not files_to_upload and not files_to_delete:
                        return {"message": "Already up to date!", "details": {"updated": 0, "deleted": 0}}

            except Exception as e:
                print(f"Smart Sync Check Error: {e}. Falling back to full.")
                mode = "full"

        if mode == "full":
            files_to_delete = [] # Full sync handles wipe on receiver side usually, but new API does merge.
                                 # WAIT: The new Student API `sync_data` does NOT wipe if we don't tell it to?
                                 # Actually, the new Student API does 'Smart Merge' if we just send files.
                                 # To do a FULL RESET with the new API, we might need a flag.
                                 # But for now, let's just stick to 'Smart' being the primary.
                                 # If we want 'Full', we basically upload EVERY file found locally.
            files_to_upload = []
            for root, dirs, files in os.walk(DATA_DIR):
                if "temp" in dirs: dirs.remove("temp")
                for file in files:
                    files_to_upload.append(Path(root) / file)
            # In 'Full' mode we might want to tell student to wipe? 
            # For this V3, 'Smart' is better. If 'Full' requested, we just send all files, 
            # but we won't explicitely wipe remote unless we list remote files.
            # Let's simplify: 'Full' just sends ALL files. 'Deletions' empty.
            pass

        # --- 2. CREATE ZIP ---
        zip_buffer = io.BytesIO()
        has_zip = False
        if files_to_upload:
            has_zip = True
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for file_path in files_to_upload:
                    archive_name = file_path.relative_to(DATA_DIR)
                    zip_file.write(file_path, archive_name)
            zip_buffer.seek(0)
        
        # --- 3. SEND ---
        multipart_data = {}
        if has_zip:
            multipart_data['file'] = ('data_sync.zip', zip_buffer, 'application/zip')
            
        data_payload = {}
        if files_to_delete:
            data_payload['deletions'] = json.dumps(files_to_delete)
            
        print(f"Sending Deploy: {len(files_to_upload)} Files, {len(files_to_delete)} Deletions")
        
        if not has_zip and not files_to_delete:
             return {"message": "Nothing to sync."}

        response = requests.post(STUDENT_APP_URL, files=multipart_data, data=data_payload)
        
        if response.status_code == 200:
            return {"message": "Deployment Successful", "mode": mode, "details": response.json()}
        else:
            raise HTTPException(status_code=502, detail=f"Student App Error: {response.text}")

    except requests.exceptions.ConnectionError:
         raise HTTPException(status_code=503, detail="Student App is not reachable (Is it running on port 8001?)")
    except Exception as e:
        print(f"Deploy Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scans/analyze")
async def analyze_scan(file: UploadFile = File(...), pages_per_copy: int = Form(2)):
    if not file.filename.lower().endswith(".pdf"):
         raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    session_id = str(uuid.uuid4())
    session_dir = DATA_DIR / "scans" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    scan_path = session_dir / "bulk.pdf"
    
    with open(scan_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    try:
        # Process and Analyze
        results = scan_analyzer.process_bulk_scan(scan_path, pages_per_chunk=pages_per_copy)
        
        # Add URL to results for frontend display
        for res in results:
             if "chunk_path" in res:
                 p = Path(res["chunk_path"])
                 # data/scans/uuid/chunks/bulk/bulk_part_1.pdf -> /content/scans/uuid/chunks/bulk/bulk_part_1.pdf
                 try:
                     rel = p.relative_to(DATA_DIR)
                     res["url"] = f"/content/{rel}"
                 except ValueError:
                     pass
                     
        return {
            "session_id": session_id,
            "results": results
        }
        
    except Exception as e:
        print(f"Analysis Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class GradeScanRequest(BaseModel):
    chunk_path: str
    student_id: Optional[str] = None
    quiz_number: Optional[str] = None
    course_id: Optional[str] = None

@app.post("/api/scans/grade")
async def grade_scan_chunk(payload: GradeScanRequest):
    try:
        # Convert quiz_number to int if present
        q_num = int(payload.quiz_number) if payload.quiz_number else None
        
        # Call grader with overrides
        result = grader.grade_submission_smart(
            scan_path=Path(payload.chunk_path),
            override_quiz_number=q_num,
            override_course_id=payload.course_id,
            override_student_id=payload.student_id
        )
        return result
    except Exception as e:
        print(f"Grading Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/student_history", response_class=HTMLResponse)
async def serve_student_history():
    with open(FRONTEND_DIR / "student_history.html", "r") as f:
        content = f.read()
    return HTMLResponse(content=content, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/api/students/{student_id}/courses/{course_id}/quizzes")
async def get_student_quizzes_detail(student_id: str, course_id: str):
    """
    Returns list of quizzes for a student in a course, including scan URL and correction data.
    """
    student_course_dir = Path(f"data/students/{student_id}/{course_id}")
    if not student_course_dir.exists():
        return []
        
    results = []
    # Iterate over quiz_X directories
    for quiz_dir in student_course_dir.glob("quiz_*"):
        try:
            # Extract number from 'quiz_2'
            q_num = int(quiz_dir.name.split("_")[1])
            
            # Look for scan.*
            scan_file = next((f for f in quiz_dir.glob("scan.*") if f.exists()), None)
            correction_file = quiz_dir / "correction.json"
            subject_file = quiz_dir / "subject.pdf" 
            
            quiz_data = {
                "quiz_number": q_num,
                "scan_url": None,
                "subject_url": None,
                "correction": None
            }
            
            if scan_file:
                rel_path = scan_file.relative_to("data")
                quiz_data["scan_url"] = f"/content/{rel_path}"

            if subject_file.exists():
                rel_path = subject_file.relative_to("data")
                quiz_data["subject_url"] = f"/content/{rel_path}"
                
            if correction_file.exists():
                with open(correction_file, "r") as f:
                    quiz_data["correction"] = json.load(f)
            
            if scan_file or quiz_data["correction"] or quiz_data["subject_url"]:
                results.append(quiz_data)
                
        except Exception as e:
            print(f"Skipping {quiz_dir}: {e}")
            continue
            
    # Sort by number
    results.sort(key=lambda x: x["quiz_number"])
    return results

