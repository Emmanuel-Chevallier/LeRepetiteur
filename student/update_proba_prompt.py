
import os
import sys
sys.path.append(os.getcwd())
from backend.database import db
from backend.generator import generate_quizzes_for_course

def update_prompt():
    courses = db.get_all_courses()
    course = next((c for c in courses if c["id"] == "proba"), None)
    if not course: return

    # New default prompt key logic
    new_prompt = """Focus on key concepts.
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
{history}"""

    grading_prompt = """Role: Strict Grader.

Context:
Original Questions (LaTeX):
{latex_context}
{course_context_injection}

Student Submission (Text/Scan):
{student_submission}

Task:
1. Transcribe answer if needed.
2. Grade /20.
3. Feedback & Weak Points in BILINGUAL FORMAT (English + French).

Output JSON:
{{
    "transcription": "...",
    "grades": [{{ "question_number": 1, "question_text": "...", "score": 4, "feedback": "Excellent work. \\n\\n Excellent travail." }}],
    "total_score": 15
}}"""

    course["custom_prompt"] = new_prompt
    course["custom_grading_prompt"] = grading_prompt
    db.save_course(course)
    print("✅ Updated 'proba' text.")

if __name__ == "__main__":
    update_prompt()
