import os
import shutil
import google.generativeai as genai
from typing import List, Dict, Any, Optional
from pathlib import Path
from backend.database import db
from backend.latex_utils import escape_latex, compile_latex

# Configuration
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    key_file = Path(__file__).parent.parent / "Gemini_key"
    if key_file.exists():
        with open(key_file, "r") as f:
            api_key = f.read().strip()

if api_key:
    genai.configure(api_key=api_key)

def generate_quizzes_for_course(
    course_id: str, 
    regenerate: bool = False, 
    specific_instructions: Optional[str] = None,
    selected_questions: str = "",
    n_new: int = 0,
    n_old: int = 0
) -> List[Dict[str, Any]]:
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
    
    # 5. Quiz Numbering logic
    if regenerate:
        quiz_count = course.get("quiz_count", 0)
        if quiz_count == 0:
            # First time, fallback to standard gen
            quiz_count = 1
            course["quiz_count"] = 1
            db.save_course(course)
        
        print(f"♻️ Regenerating Quiz #{quiz_count} for {len(target_students)} students...")

    else:
        quiz_count = course.get("quiz_count", 0) + 1
        course["quiz_count"] = quiz_count
        db.save_course(course)
        print(f"Generating Quiz #{quiz_count} for {len(target_students)} students...")
        
    # Save the selected questions bank for this quiz
    if selected_questions:
        bank_path = Path(f"data/courses/{course_id}/quiz_{quiz_count}_selected_bank.json")
        bank_path.parent.mkdir(parents=True, exist_ok=True)
        db._write_json(bank_path, {
            "quiz_number": quiz_count,
            "n_new": n_new,
            "n_old": n_old,
            "selected_questions": selected_questions
        })
    
    generated_quizzes = []

    total_students = len(target_students)
    for i, student in enumerate(target_students):
        # Yield Progress
        s_name = f"{student.get('last_name', '')} {student.get('first_name', '')}".strip() or student["id"]
        yield {"type": "progress", "current": i + 1, "total": total_students, "message": f"Generating for {s_name}..."}
        
        # Cleanup existing quiz data before regeneration
        if regenerate:
            cleanup_existing_quiz(student["id"], course_id, quiz_count)
        
        quiz = generate_single_quiz(student, course, content_context, quiz_count, specific_instructions, selected_questions, n_new, n_old)
        generated_quizzes.append(quiz)

    # 6. Global Compilation
    yield {"type": "progress", "current": total_students, "total": total_students, "message": "Compiling Global PDF..."}
    global_pdf_path = compile_global_pdf(course, generated_quizzes, quiz_count)
    
    global_pdf_url = None
    if global_pdf_path:
        # data/courses/test/all_quizzes_1.pdf -> /content/courses/test/all_quizzes_1.pdf
        try:
            rel = global_pdf_path.relative_to("data")
            global_pdf_url = f"/content/{rel}"
            print(f"global_pdf_url assigned: {global_pdf_url}")
        except Exception as e:
            print(f"Error generating URL: {e}")

    yield {"type": "result", "count": len(generated_quizzes), "quizzes": generated_quizzes, "global_pdf_url": global_pdf_url}

def generate_single_quiz(
    student: Dict, 
    course: Dict, 
    context: str, 
    quiz_number: int, 
    specific_instructions: Optional[str] = None,
    selected_questions: str = "",
    n_new: int = 0,
    n_old: int = 0
) -> Dict:
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

    custom_prompt = course.get("custom_prompt", """Concentrez-vous sur les concepts clés.
Assurez-vous que les questions sont de difficulté progressive.

Formatage :
- Utilisez l'environnement `enumerate`.
- RETOURNEZ UNIQUEMENT LE CODE LATEX à l'intérieur de enumerate. Pas de conteneur de document.
- IMPORTANT : Chaque question doit être formulée dans la langue originale du cours, suivie d'une traduction en français (si le cours n'est pas en français). 
  Format : 
  \\item Texte dans la langue originale \\\\ \\textit{Texte en Français}
- IMPORTANT : Limitez le contenu à 1,5 page maximum (environ 80 lignes).
- CRITIQUE : PAS DE CASES DE RÉPONSE, PAS DE CADRES, PAS DE MINIPAGES, PAS DE VSPACE. Ne laissez pas d'espace ou de lignes pour que l'étudiant écrive sa réponse. Écrivez juste la question et rien d'autre.
- ASSUREZ-VOUS QUE CHAQUE QUESTION EST DANS LA LANGUE ORIGINALE ET EN FRANÇAIS.
- Le formatage doit être clair et lisible.
- Commencez chaque nouvelle question par `\\item`.

Tâche :
Créez un corps d'examen LaTeX (questions uniquement) avec 4 questions :
- 2 questions sur le matériel le plus *récent* dans le contexte (partie commune).
- regardez les questions échouées dans son historique, et cherchez 2 questions qui n'ont jamais été résolues. Si vous en trouvez, posez-les.
- si nécessaire, posez plus de questions sur le matériel de cours pour arriver à 4 questions au total.
- ASSUREZ-VOUS QUE CHAQUE QUESTION EST DANS LA LANGUE ORIGINALE ET EN FRANÇAIS.

Historique de l'étudiant :
{history}""")
    
    # Support Placeholders
    if "{history}" in custom_prompt:
        custom_prompt = custom_prompt.replace("{history}", history_str)
    # Legacy support
    if "{weak_points}" in custom_prompt:
         custom_prompt = custom_prompt.replace("{weak_points}", history_str)
    
    if "{context}" in custom_prompt:
        custom_prompt = custom_prompt.replace("{context}", context[:15000])
        default_context_injection = ""
    else:
        default_context_injection = f"\nCourse Context (LaTeX):\n{context[:15000]}"
        
    if "{selected_questions}" in custom_prompt:
        custom_prompt = custom_prompt.replace("{selected_questions}", selected_questions)
        
    if "{n_new}" in custom_prompt:
        custom_prompt = custom_prompt.replace("{n_new}", str(n_new))
        
    if "{n_old}" in custom_prompt:
        custom_prompt = custom_prompt.replace("{n_old}", str(n_old))
        
    if "{n_total}" in custom_prompt:
        custom_prompt = custom_prompt.replace("{n_total}", str(n_new + n_old))
    
    # Anonymized Prompt
    prompt = f"""
    Rôle : Professeur créant un examen.
    
    ID Étudiant : {student['id']}
    
    Instructions de l'enseignant :
    {custom_prompt} {default_context_injection}

    Informations spécifiques :
    {specific_instructions}
    """
    
    if specific_instructions:
        prompt = prompt.replace("{specific_instructions}", specific_instructions)
    else:
        prompt = prompt.replace("Informations spécifiques :\n    {specific_instructions}", "")

    # 2. Call Gemini
    latex_body = ""
    if not api_key:
        print("Warning: No API Key. Using mock content.")
        latex_body = r"\item Mock Question 1?"
    else:
        try:
            model = genai.GenerativeModel('gemini-3-pro-preview')
            response = model.generate_content(prompt)
            latex_body = response.text
            # Cleanup
            latex_body = latex_body.replace("```latex", "").replace("```", "")
            # Strip redundant enumerate wrappers if present
            latex_body = latex_body.replace("\\begin{enumerate}", "").replace("\\end{enumerate}", "")
            
            # Explicitly remove hallucinated answer boxes
            import re
            latex_body = re.sub(r'\\fbox\{\\begin\{minipage\}.*?\\end\{minipage\}\}', '', latex_body, flags=re.DOTALL)
            latex_body = re.sub(r'\\vspace\{.*?\}', '', latex_body)
            # Remove empty lines left behind
            latex_body = re.sub(r'\n\s*\n', '\n\n', latex_body)

        except Exception as e:
            print(f"Gemini Error: {e}")
            latex_body = r"\item Error generating questions."

    # 3. Create Full PDF
    # Use "Candidate #{id}" in Author field
    s_display = f"Candidate #{student['id']}"
    
    full_latex = f"""
\\documentclass[a4paper,12pt]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage{{enumitem}}
\\usepackage{{geometry}}
\\usepackage{{fancyhdr}}
\\usepackage{{lastpage}}
\\usepackage{{amsmath}}
\\usepackage{{amssymb}}

\\geometry{{margin=2cm}}

% Header Setup
\\pagestyle{{fancy}}
\\fancyhf{{}}
\\lhead{{\\textbf{{Quiz \\#{quiz_number} - Student \\#{student['id']}}}}}
\\rhead{{\\today}}
\\cfoot{{\\thepage}}

\\title{{Quiz \\#{quiz_number}: {escape_latex(course['title'])}}}
\\author{{{escape_latex(s_display)}}}
\\date{{\\today}}

\\begin{{document}}

\\section*{{Questions}}
\\begin{{enumerate}}[label=\\arabic*)]
{latex_body}
\\end{{enumerate}}

% Ensure Even Number of Pages (for double-sided printing)
\\clearpage
\\ifodd\\value{{page}}\\else\\hbox{{}}\\newpage\\fi

\\end{{document}}
    """
    
    # Save & Compile
    # NEW PATH: data/students/{student_id}/{course_id}/quiz_{quiz_number}/
    quiz_dir = Path(f"data/students/{student['id']}/{course['id']}/quiz_{quiz_number}")
    quiz_dir.mkdir(parents=True, exist_ok=True)
    
    # Save course context used for this generation
    with open(quiz_dir / "course_context.tex", "w", encoding="utf-8") as f:
        f.write(context)
    
    filename_base = "subject"
    
    pdf_path = compile_latex(full_latex, quiz_dir, filename_base)
    
    # 4. Save Record (Update path)
    quiz_record = {
        "id": f"{course['id']}_{quiz_number}_{student['id']}",
        "course_id": course["id"],
        "student_id": student["id"],
        "student_name": f"{student.get('last_name', '')} {student.get('first_name', '')}".strip() or student["id"],
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


def cleanup_existing_quiz(student_id: str, course_id: str, quiz_number: int):
    """
    Remove all data associated with an existing quiz for a student:
    - correction.json & scan.* from the quiz directory
    - The entry in history.json
    - The entry in quizzes.json (global registry)
    """
    print(f"🧹 Cleanup: student={student_id}, course={course_id}, quiz={quiz_number}")
    
    # 1. Delete correction.json and scan.* from quiz directory
    quiz_dir = Path(f"data/students/{student_id}/{course_id}/quiz_{quiz_number}")
    if quiz_dir.exists():
        for pattern in ["correction.json", "scan.*"]:
            for f in quiz_dir.glob(pattern):
                print(f"  Deleting {f}")
                f.unlink()
    
    # 2. Remove from history.json
    history_path = Path(f"data/students/{student_id}/history.json")
    if history_path.exists():
        history = db._read_json(history_path)
        past = history.get("past_quizzes", [])
        original_len = len(past)
        history["past_quizzes"] = [
            q for q in past
            if not (q.get("course_id") == course_id and str(q.get("quiz_number")) == str(quiz_number))
        ]
        removed = original_len - len(history["past_quizzes"])
        if removed > 0:
            print(f"  Removed {removed} entry from history.json")
            db._write_json(history_path, history)
    
    # 3. Remove from quizzes.json (global registry)
    quizzes_reg_path = Path("data/global/quizzes.json")
    quizzes_reg = db._read_json(quizzes_reg_path)
    original_len = len(quizzes_reg)
    filtered = [
        q for q in quizzes_reg
        if not (
            q.get("course_id") == course_id
            and str(q.get("quiz_number")) == str(quiz_number)
            and q.get("student_id") == student_id
        )
    ]
    if len(filtered) < original_len:
        print(f"  Removed {original_len - len(filtered)} entry from quizzes.json")
        db._write_json(quizzes_reg_path, filtered)


def recompile_global_pdf(course_id: str, quiz_number: int) -> Optional[Path]:
    """
    Recompile all_quizzes_{N}.pdf by gathering all existing subject.pdf files 
    for the given quiz number from all enrolled students.
    """
    courses = db.get_all_courses()
    course = next((c for c in courses if c["id"] == course_id), None)
    if not course:
        print(f"Course {course_id} not found for recompilation.")
        return None
    
    enrolled_ids = course.get("enrolled_students", [])
    
    # Gather all existing subject PDFs for this quiz
    quizzes = []
    for sid in sorted(enrolled_ids):
        pdf_path = Path(f"data/students/{sid}/{course_id}/quiz_{quiz_number}/subject.pdf")
        if pdf_path.exists():
            quizzes.append({"pdf_path": str(pdf_path), "student_id": sid})
    
    if not quizzes:
        print("No PDFs found for recompilation.")
        return None
    
    return compile_global_pdf(course, quizzes, quiz_number)


def _get_current_context(course: Dict) -> str:
    """
    Read the course LaTeX file and extract the content between start_line and end_line.
    This is the 'current context' based on page settings.
    """
    latex_path_str = course.get("latex_file_path", "")
    if not latex_path_str:
        raise ValueError("No LaTeX source file uploaded for this course.")
    latex_path = Path(latex_path_str)
    if not latex_path.exists():
        raise ValueError(f"Source file not found: {latex_path}")
    
    with open(latex_path, "r") as f:
        full_content = f.read()
    
    lines = full_content.splitlines()
    start_line = course.get("start_line", 0)
    end_line = course.get("end_line")
    if end_line is None or end_line > len(lines):
        end_line = len(lines)
    return "\n".join(lines[start_line:end_line])


def generate_quiz_for_student(
    course_id: str, 
    student_id: str, 
    quiz_number: int, 
    specific_instructions: Optional[str] = None, 
    context_source: str = "current",
    selected_questions: str = "",
    n_new: int = 0,
    n_old: int = 0
):
    """
    Generate/regenerate a quiz for a single student.
    Yields progress events (streaming).
    context_source: "current" = use page start/end lines, "existing" = use saved course_context.tex
    """
    # 1. Fetch Course
    courses = db.get_all_courses()
    course = next((c for c in courses if c["id"] == course_id), None)
    if not course:
        raise ValueError(f"Course {course_id} not found")
    
    # 2. Fetch Student
    students = db.get_all_students()
    student = next((s for s in students if s["id"] == student_id), None)
    if not student:
        raise ValueError(f"Student {student_id} not found")
    
    # 3. Get Course Content based on context_source
    if context_source == "existing":
        # Try to read saved course_context.tex from existing quiz folder
        existing_context_path = Path(f"data/students/{student_id}/{course_id}/quiz_{quiz_number}/course_context.tex")
        if existing_context_path.exists():
            with open(existing_context_path, "r", encoding="utf-8") as f:
                content_context = f.read()
            print(f"📁 Using EXISTING context from {existing_context_path}")
        else:
            print(f"⚠️ No existing context found at {existing_context_path}, falling back to current context")
            content_context = _get_current_context(course)
    else:
        content_context = _get_current_context(course)
    
    # 4. Update quiz_count if this is a new quiz number beyond current count
    current_count = course.get("quiz_count", 0)
    if quiz_number > current_count:
        course["quiz_count"] = quiz_number
        db.save_course(course)
        
    # Save the selected questions bank for this quiz
    # For individual regeneration, don't overwrite the main bank — add an override entry
    if selected_questions:
        bank_path = Path(f"data/courses/{course_id}/quiz_{quiz_number}_selected_bank.json")
        bank_path.parent.mkdir(parents=True, exist_ok=True)
        
        if bank_path.exists():
            existing = db._read_json(bank_path)
            if isinstance(existing, dict):
                # Add override entry
                if "overrides" not in existing:
                    existing["overrides"] = []
                from datetime import datetime
                existing["overrides"].append({
                    "student_id": student_id,
                    "timestamp": datetime.now().isoformat(),
                    "n_new": n_new,
                    "n_old": n_old,
                    "selected_questions": selected_questions
                })
                db._write_json(bank_path, existing)
        else:
            # No existing bank — create it as the main bank
            db._write_json(bank_path, {
                "quiz_number": quiz_number,
                "n_new": n_new,
                "n_old": n_old,
                "selected_questions": selected_questions
            })
    
    # 5. Cleanup existing data
    student_name = f"{student.get('last_name', '')} {student.get('first_name', '')}".strip() or student["id"]
    yield {"type": "progress", "current": 0, "total": 1, "message": f"Cleaning up old data for {student_name}..."}
    cleanup_existing_quiz(student_id, course_id, quiz_number)
    
    # 6. Generate
    yield {"type": "progress", "current": 1, "total": 1, "message": f"Generating Quiz #{quiz_number} for {student_name}..."}
    quiz = generate_single_quiz(student, course, content_context, quiz_number, specific_instructions, selected_questions, n_new, n_old)
    
    # 7. Recompile global PDF
    yield {"type": "progress", "current": 1, "total": 1, "message": "Recompiling global PDF..."}
    global_pdf_path = recompile_global_pdf(course_id, quiz_number)
    
    global_pdf_url = None
    if global_pdf_path:
        try:
            rel = global_pdf_path.relative_to("data")
            global_pdf_url = f"/content/{rel}"
        except Exception:
            pass
    
    yield {"type": "result", "count": 1, "quizzes": [quiz], "global_pdf_url": global_pdf_url}

def compile_global_pdf(course: Dict, quizzes: List[Dict], quiz_number: int) -> Optional[Path]:
    """
    Concatenates all separately generated quiz PDFs into a single master PDF using pdfpages.
    """
    if not quizzes:
        return None
        
    print(f"Compiling Global PDF for Quiz #{quiz_number} ({len(quizzes)} students)...")
    
    # Check if quizzes have PDF paths
    valid_pdfs = [q['pdf_path'] for q in quizzes if q.get('pdf_path')]
    
    if not valid_pdfs:
        print("No valid PDFs to concatenate.")
        return None

    import shutil
    import tempfile
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        includes = ""
        for i, pdf_path in enumerate(valid_pdfs):
            # Copy to temp dir with safe ASCII name to avoid pdflatex errors with accents/spaces
            safe_name = f"quiz_{i}.pdf"
            safe_path = temp_dir_path / safe_name
            shutil.copy2(pdf_path, safe_path)
            
            # Abs path
            abs_path = str(safe_path.resolve())
            # LaTeX friendly path (forward slashes)
            abs_path = abs_path.replace("\\", "/")
            includes += f"\\includepdf[pages=-]{{{abs_path}}}\n"

        master_latex = f"""
\\documentclass[a4paper]{{article}}
\\usepackage{{pdfpages}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}

\\begin{{document}}
% Concatenation of all student quizzes
{includes}
\\end{{document}}
        """
        
        # 2. Save & Compile INSIDE temp dir to avoid parentheses/accents in working directory
        filename = f"all_quizzes_{quiz_number}"
        temp_pdf_path = compile_latex(master_latex, temp_dir_path, filename)
        
        course_dir = Path(f"data/courses/{course['id']}")
        course_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = course_dir / f"{filename}.pdf"
        
        if temp_pdf_path and temp_pdf_path.exists():
            shutil.copy2(temp_pdf_path, pdf_path)
            print(f"Global PDF saved: {pdf_path}")
            return pdf_path
            
        print("Failed to compile global PDF inside temp directory.")
        return None

def generate_question_bank(course_id: str, prompt_text: str, num_questions: int = 10) -> List[str]:
    """
    Generate a bank of questions based on the course context using gemini-3.1-pro-preview.
    """
    if not api_key:
        raise ValueError("No Gemini API Key found.")
        
    courses = db.get_all_courses()
    course = next((c for c in courses if c["id"] == course_id), None)
    if not course:
        raise ValueError(f"Course {course_id} not found")
        
    content_context = _get_current_context(course)
    
    full_prompt = prompt_text
    if "{num_questions}" in full_prompt:
        full_prompt = full_prompt.replace("{num_questions}", str(num_questions))
        
    if "{course_segment}" in full_prompt:
        full_prompt = full_prompt.replace("{course_segment}", content_context[:15000])
    else:
        full_prompt += f"\n\nCourse Context (LaTeX):\n{content_context[:15000]}"
    
    print(f"Calling gemini-3.1-pro-preview for question bank generation...")
    model = genai.GenerativeModel('gemini-3.1-pro-preview')
    response = model.generate_content(full_prompt)
    raw_text = response.text
    
    # Cleanup
    raw_text = raw_text.replace("```latex", "").replace("```", "")
    raw_text = raw_text.replace("\\begin{enumerate}", "").replace("\\end{enumerate}", "")
    
    # Parse by \item
    parts = raw_text.split("\\item")
    questions = []
    
    # The first part is before the first \item, ignore it
    for part in parts[1:]:
        cleaned = part.strip()
        if cleaned:
            questions.append(f"\\item {cleaned}")
            
    return questions
