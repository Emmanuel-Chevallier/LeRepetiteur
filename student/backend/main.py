from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path
from backend.database import db
from backend import generator, grader, gradebook

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
        return f.read()

# --- Auth ---
@app.post("/api/login")
async def login(payload: dict):
    # Payload: {"id": "...", "password": "..."}
    sid = payload.get("id")
    pwd = payload.get("password")
    
    if not sid or not pwd:
         raise HTTPException(status_code=400, detail="Missing credentials")
         
    student = next((s for s in db.get_all_students() if s["id"] == sid), None)
    
    if not student:
        raise HTTPException(status_code=401, detail="Invalid ID")
        
    # Check password
    # In real app, hash this. Here plain text as per spec.
    if student.get("password") != pwd:
         raise HTTPException(status_code=401, detail="Invalid Password")
         
    return {"message": "Login successful", "student": {"id": student["id"], "first_name": student.get("first_name", ""), "last_name": student.get("last_name", "")}}

# --- API Endpoints ---
@app.get("/api/students")
def get_students():
    return db.get_all_students()

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
    return {"message": "Student added", "student": student}

@app.delete("/api/students/{student_id}")
async def delete_student(student_id: str):
    # Remove from global list
    students = db.get_all_students()
    new_list = [s for s in students if s["id"] != student_id]
    
    if len(new_list) == len(students):
        raise HTTPException(status_code=404, detail="Student not found")
        
    db._write_json(Path("data/global/students.json"), new_list)
    
    # Optional: cleanup data folder?
    # Implementation plan decision: Remove from enrolled lists?
    # Let's remove from enrolled lists in courses.
    courses = db.get_all_courses()
    for c in courses:
        if "enrolled_students" in c and student_id in c["enrolled_students"]:
            c["enrolled_students"].remove(student_id)
            db.save_course(c)
            
    return {"message": "Student deleted"}

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

from backend.generator import generate_quizzes_for_course

@app.post("/api/courses/{course_id}/generate")
async def generate_quizzes(course_id: str, payload: dict = Body(None)):
    try:
        # Update settings if provided
        if payload and "custom_prompt" in payload:
             db.update("courses", course_id, {"custom_prompt": payload["custom_prompt"]})
             
        quizzes = generate_quizzes_for_course(course_id)
        return {"message": "Generation successful", "count": len(quizzes), "quizzes": quizzes}
    except Exception as e:
        print(f"Generation Error: {e}")
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
    include_context: bool = Form(False)
):
    # 1. Save Temp
    temp_dir = Path("data/temp")
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / file.filename
    print(f"DEBUG: Saved temp file to {temp_path} (name={file.filename})")
    
    with open(temp_path, "wb+") as f:
        shutil.copyfileobj(file.file, f)
        
    # 2. Smart Grade
    try:
        result = grade_submission_smart(temp_path, custom_prompt=custom_prompt, include_context=include_context)
        # Cleanup temp? Maybe keep for debug?
        return {"message": "Smart Grading Complete", "result": result}
    except Exception as e:
        print(f"Smart Grading Error: {e}")
        return {"message": "Smart Grading Failed", "error": str(e)}

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
    return {"status": "ok"}

from backend.chatbot import get_chat_response
from pydantic import BaseModel
from typing import List, Dict

from typing import Optional

class ChatRequest(BaseModel):
    student_id: str
    course_id: Optional[str] = None # Optional context
    message: str
    history: List[Dict[str, str]] = []

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    return StreamingResponse(
        get_chat_response(req.student_id, req.message, req.history, req.course_id),
        media_type="text/plain"
    )

import json

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
                # relative path from 'data' root for static serving
                # scan_file relative to CWD is 'data/students/...'
                # We need '/content/students/...'
                rel_path = scan_file.relative_to("data")
                quiz_data["scan_url"] = f"/content/{rel_path}"

            if subject_file.exists():
                rel_path = subject_file.relative_to("data")
                quiz_data["subject_url"] = f"/content/{rel_path}"
                
            if correction_file.exists():
                with open(correction_file, "r") as f:
                    quiz_data["correction"] = json.load(f)
            
            # Only add if we have something
            if scan_file or quiz_data["correction"] or quiz_data["subject_url"]:
                results.append(quiz_data)
                
        except Exception as e:
            print(f"Skipping {quiz_dir}: {e}")
            continue
            
    # Sort by number
    results.sort(key=lambda x: x["quiz_number"])
    return results


import zipfile
import io
import shutil
import os


from backend.sync_utils import generate_manifest

@app.get("/api/sync/manifest")
async def get_manifest():
    """Returns the Manifest (Hash Map) of the current data state."""
    return generate_manifest(DATA_DIR)

@app.post("/api/sync")
async def sync_data(
    file: UploadFile = File(None), 
    deletions: str = Form(None) # JSON string of list[str]
):
    """
    Receives a ZIP file (optional) and a list of deletions (optional).
    If ZIP provided, unzips/overwrites.
    If Deletions provided, deletes those files.
    """
    import json
    
    try:
        # 1. Process Deletions First (cleanup)
        if deletions:
            try:
                delete_list = json.loads(deletions)
                for rel_path in delete_list:
                    # Security check: prevent deletion outside data dir
                    target_path = (DATA_DIR / rel_path).resolve()
                    if DATA_DIR.resolve() in target_path.parents or target_path == DATA_DIR.resolve(): # Should be child
                         if target_path.exists():
                             if target_path.is_dir():
                                 shutil.rmtree(target_path)
                             else:
                                 target_path.unlink()
            except json.JSONDecodeError:
                print("Invalid deletions JSON")

        # 2. Extract Updates (Smart Merge)
        if file:
            content = await file.read()
            zip_file = zipfile.ZipFile(io.BytesIO(content))
            zip_file.extractall(DATA_DIR)
            
            return {"message": "Smart Sync Successful", "files_updated": len(zip_file.namelist()), "files_deleted": len(json.loads(deletions)) if deletions else 0}
            
        return {"message": "Sync Completed (Deletions Only)", "files_updated": 0}
        
    except Exception as e:
        print(f"Sync Error: {e}")
        raise HTTPException(status_code=500, detail=f"Sync Failed: {str(e)}")

