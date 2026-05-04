import os
import google.generativeai as genai
from typing import List, Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel
import json
from pathlib import Path
from backend.database import db
from backend.latex_utils import escape_latex, compile_latex
from backend.config import API_KEY

if API_KEY:
    genai.configure(api_key=API_KEY)

def generate_quizzes_for_course(course_id: str) -> List[Dict[str, Any]]:
    # 1. Fetch Course Data
    courses = db.get_all_courses()
    course = next((c for c in courses if c["id"] == course_id), None)
    if not course:
        raise ValueError(f"Course {course_id} not found")

    # 2. Get Course Content
    latex_path_str = course.get("latex_file_path", "")
    if not latex_path_str:
        raise ValueError("No LaTeX source file uploaded for this course.")
        
    latex_path = Path(latex_path_str)
    if not latex_path.exists() or not latex_path.is_file():
         raise ValueError(f"Source file not found or invalid: {latex_path}")
    
    with open(latex_path, "r") as f:
        full_content = f.read()

    # 3. Truncate Content based on Interval
    start_line = course.get("start_line", 0)
    end_line = course.get("end_line")
    
    lines = full_content.splitlines()
    
    # Validation
    if end_line is None or end_line > len(lines):
        end_line = len(lines)
        
    content_context = "\n".join(lines[start_line:end_line])
    print(f"Content Interval: {start_line} to {end_line} ({len(lines[start_line:end_line])} lines).")

    # 4. Fetch Enrolled Students
    students = db.get_all_students() 
    enrolled_ids = course.get("enrolled_students", [])
    target_students = [s for s in students if s["id"] in enrolled_ids] if enrolled_ids else students
    
    # 5. Quiz Numbering
    quiz_count = course.get("quiz_count", 0) + 1
    course["quiz_count"] = quiz_count
    db.save_course(course) # Persist count
    
    print(f"Generating Quiz #{quiz_count} for {len(target_students)} students...")
    
    generated_quizzes = []

    for student in target_students:
        quiz = generate_single_quiz(student, course, content_context, quiz_count)
        generated_quizzes.append(quiz)

    # 6. Global Compilation
    compile_global_pdf(course, generated_quizzes, quiz_count)

    return generated_quizzes

def generate_single_quiz(student: Dict, course: Dict, context: str, quiz_number: int) -> Dict:
    # 1. Prepare Prompt
    history = db.get_student_history(student["id"])
    
    # Format History
    past_quizzes = history.get("past_quizzes", [])
    history_str = ""
    if past_quizzes:
        history_str += "PREVIOUS QUIZZES & CORRECTIONS:\n"
        for q in past_quizzes:
            # Filter by course if needed? The user said "of each previous quizz of the course".
            if q.get("course_id") == course["id"]:
                history_str += f"\n--- Quiz #{q.get('quiz_number')} ---\n"
                correction = q.get("correction", {})
                # Format grades/feedback
                for g in correction.get("grades", []):
                     history_str += f"Q: {g.get('question_text', 'N/A')}\n"
                     history_str += f"Score: {g.get('score')}/5\n"
                     history_str += f"Feedback: {g.get('feedback')}\n"
    
    if not history_str:
        history_str = "No previous quizzes."

    custom_prompt = course.get("custom_prompt", """Focus on key concepts.
Ensure questions are progressive in difficulty.

Formatting:
- Use `enumerate` environment.
- RETURN ONLY THE LATEX CODE inside the enumerate. No document wrappers.
- IMPORTANT: All questions must be BILINGUAL. 
  Format: 
  \\item English Text \\\\ \\textit{Texte en Français}
- IMPORTANT: After each question, provide an answer box:
  \\begin{center}
  \\framebox[\\textwidth]{\\rule{0pt}{5cm}}
  \\end{center}

Task:
Create a LaTeX exam body (questions only) with 4 questions:
- 2 Questions on the *newest* material in the context (Common part).
- 2 Questions specifically addressing the student's weaknesses/history (Personalized part).
- ENSURE EACH QUESTION IS IN ENGLISH AND FRENCH.

Student History:
{history}""")
    
    # Support Placeholders
    if "{history}" in custom_prompt:
        custom_prompt = custom_prompt.replace("{history}", history_str)
    # Legacy support
    if "{weak_points}" in custom_prompt:
         custom_prompt = custom_prompt.replace("{weak_points}", history_str)
    
    # Anonymized Prompt
    prompt = f"""
    Role: Professor creating an exam.
    
    Course Context (LaTeX):
    {context[:15000]} 
    
    Student ID: {student['id']}
    
    Teacher Instructions:
    {custom_prompt}
    """

    # 2. Call Gemini
    latex_body = ""
    if not api_key:
        print("Warning: No API Key. Using mock content.")
        latex_body = r"\item Mock Question 1? \begin{center}\framebox[\textwidth]{\rule{0pt}{5cm}}\end{center}"
    else:
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            latex_body = response.text
            # Cleanup
            latex_body = latex_body.replace("```latex", "").replace("```", "")
        except Exception as e:
            print(f"Gemini Error: {e}")
            latex_body = r"\item Error generating questions. \begin{center}\framebox[\textwidth]{\rule{0pt}{5cm}}\end{center}"

    # 3. Create Full PDF
    # Use "Candidate #{id}" in Author field
    s_display = f"Candidate #{student['id']}"
    
    full_latex = f"""
\\documentclass[a4paper,12pt]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage{{geometry}}
\\geometry{{margin=2cm}}

\\title{{Quiz #{quiz_number}: {escape_latex(course['title'])}}}
\\author{{{escape_latex(s_display)}}}
\\date{{\\today}}

\\begin{{document}}
\\maketitle

\\section*{{Instructions}}
Answer all questions in the boxes provided.

\\begin{{enumerate}}
{latex_body}
\\end{{enumerate}}

\\end{{document}}
    """
    
    # Save & Compile
    # NEW PATH: data/students/{student_id}/{course_id}/quiz_{quiz_number}/
    quiz_dir = Path(f"data/students/{student['id']}/{course['id']}/quiz_{quiz_number}")
    quiz_dir.mkdir(parents=True, exist_ok=True)
    
    filename_base = f"subject" # Simple name inside the structured folder? Or keep descriptive?
    # User said: "il y a les fichiers du quizz générés"
    # Let's keep a descriptive name but cleaner.
    filename_base = "subject"
    
    pdf_path = compile_latex(full_latex, quiz_dir, filename_base)
    
    # 4. Save Record (Update path)
    quiz_record = {
        "id": f"{course['id']}_{quiz_number}_{student['id']}",
        "course_id": course["id"],
        "student_id": student["id"],
        "student_name": student["name"],
        "quiz_number": quiz_number,
        "latex_content": latex_body,
        "pdf_path": str(pdf_path) if pdf_path else None,
        "dir_path": str(quiz_dir)
    }
    
    quizzes_reg_path = Path("data/global/quizzes.json")
    quizzes_reg = db._read_json(quizzes_reg_path)
    quizzes_reg.append(quiz_record)
    db._write_json(quizzes_reg_path, quizzes_reg)
    
    return quiz_record

def compile_global_pdf(course: Dict, quizzes: List[Dict], quiz_number: int) -> Optional[Path]:
    """
    Concatenates all quizzes into a single master PDF.
    """
    if not quizzes:
        return None
        
    print(f"Compiling Global PDF for Quiz #{quiz_number} ({len(quizzes)} students)...")
    
    # 1. Start Master LaTeX
    master_latex = f"""
\\documentclass[a4paper,12pt]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage{{geometry}}
\\usepackage{{titlesec}}
\\geometry{{margin=2cm}}

\\title{{Global Compilation: Quiz #{quiz_number}}}
\\author{{{escape_latex(course['title'])}}}
\\date{{\\today}}

\\begin{{document}}
\\maketitle
\\tableofcontents
\\newpage
    """
    
    # 2. Append Each Quiz
    for q in quizzes:
        # Fetch student name again (it's in the quiz record, strictly speaking it's "student_id", 
        # but check if we have name. The 'generate_single_quiz' returns a record with IDs.
        # We need to resolve name or pass it in. 
        # Actually `generate_quizzes_for_course` has student objects. 
        # Let's augment the return of `generate_single_quiz` or `generated_quizzes` list in the main loop to include name.
        # Efficient fix: In `generate_single_quiz`, add "student_name": student["name"] to record.
        
        # NOTE: I need to update generate_single_quiz to include student_name first?
        # Or just trust that the record *will* have it if I add it now?
        # Let's add it to the record in generate_single_quiz below *this* change or implicit assume it.
        # Wait, I am editing the file at the bottom. I can't easily change the middle content in the same `replace_file_content` if it's far away.
        # I'll rely on looking up student name from DB or (lazy way) just use ID if name missing.
        # Better: use `db.get_student(q['student_id'])`? No, too many reads.
        
        # Let's assume I fix `generate_single_quiz` in a separate step or just do it here if range allows.
        # Range does not allow. I will add `student_name` to the record in `generate_single_quiz` in a separate call.
        
        # For now, placeholder or fetch.
        s_name = q.get("student_name", f"Student {q['student_id']}")
        
        chunk = f"""
\\section{{{escape_latex(s_name)}}}
\\begin{{enumerate}}
{q['latex_content']}
\\end{{enumerate}}
\\newpage
        """
        master_latex += chunk

    master_latex += "\\end{document}"
    
    # 3. Save & Compile
    # data/courses/{course_id}/
    course_dir = Path(f"data/courses/{course['id']}")
    course_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"all_quizzes_{quiz_number}"
    pdf_path = compile_latex(master_latex, course_dir, filename)
    
    if pdf_path:
        print(f"Global PDF saved: {pdf_path}")
        
    return pdf_path
