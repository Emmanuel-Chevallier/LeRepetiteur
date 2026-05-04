import os
import json
import google.generativeai as genai
from typing import List, Dict, Any
from pathlib import Path
from backend.database import db, DATA_DIR

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    key_file = Path(__file__).parent.parent / "Gemini_key"
    if key_file.exists():
        with open(key_file, "r") as f:
            api_key = f.read().strip()

if api_key:
    genai.configure(api_key=api_key)

def get_chat_response(student_id: str, message: str, chat_history: List[Dict[str, str]], course_id: str = None) -> str:
    # 1. Gather Context
    student = next((s for s in db.get_all_students() if s["id"] == student_id), None)
    if not student:
        return "Error: Student not found."
        
    history = db.get_student_history(student_id)
    past_quizzes = history.get("past_quizzes", [])
    
    # A. Course Context (Full Content)
    course_context = "No specific course selected."
    if course_id:
        courses = db.get_all_courses()
        course = next((c for c in courses if c["id"] == course_id), None)
        if course:
            latex_path = course.get("latex_file_path")
            if latex_path and os.path.exists(latex_path):
                try:
                    with open(latex_path, "r") as f:
                        # Limit to ~50k chars to avoid blowing context? Gemini 2.0 Flash has 1M.
                        # We can likely afford full content.
                        course_context = f"FULL COURSE CONTENT ({course['title']}):\n" + f.read()
                except:
                    course_context = "Error reading course file."
    
    # B. Detailed Quiz History (Dynamic Crawl)
    # We ignore db.get_student_history to ensure we get the latest files on disk
    history_context = ""
    student_dir = DATA_DIR / "students" / student_id
    if student_dir.exists():
        past_quizzes = []
        # Walk through all course folders
        for course_dir in student_dir.iterdir():
            if not course_dir.is_dir(): continue
            cid = course_dir.name
            
            # Walk through all quiz folders
            for quiz_dir in course_dir.glob("quiz_*"):
                try:
                    qnum = int(quiz_dir.name.split("_")[1])
                    correction_path = quiz_dir / "correction.json"
                    
                    if correction_path.exists():
                        with open(correction_path, "r") as f:
                            correction = json.load(f)
                            # Handle different formats if needed, but assuming valid JSON
                            past_quizzes.append({
                                "course_id": cid,
                                "quiz_number": qnum,
                                "correction": correction
                            })
                except Exception as e:
                    # Silently skip bad files or log if needed
                    continue
        
        # Sort by course then quiz number (or just simple sort)
        past_quizzes.sort(key=lambda x: (x["course_id"], x["quiz_number"]))
        
        # Sort by course then quiz number (or just simple sort)
        past_quizzes.sort(key=lambda x: (x["course_id"], x["quiz_number"]))

        for quiz in past_quizzes:
            correction = quiz.get("correction", {})
            cid = quiz["course_id"]
            qnum = quiz["quiz_number"]
            
            history_context += f"\n--- Quiz #{qnum} (Course: {cid}) ---\n"
            
            if "grades" in correction:
                for g in correction["grades"]:
                    q_text = g.get("question_text", "N/A")
                    score = g.get("score", 0)
                    feedback = g.get("feedback", "")
                    
                    history_context += f"Q: {q_text}\n"
                    history_context += f"Score: {score}\n"
                    history_context += f"Feedback: {feedback}\n"
            else:
                 history_context += "No detailed grading available.\n"
    
    if not history_context:
        history_context = "No previous quizzes found."

    
    system_prompt = f"""
    Role: Personal Tutor for student {student['name']}.
    
    You have access to:
    1. The FULL COURSE CONTENT of the subject the student is studying right now.
    2. The COMPLETE HISTORY of the student's past quizzes (questions, scores, feedback).
    
    {course_context}
    
    STUDENT HISTORY:
    {history_context}
    
    Instructions:
    - Answer the student's questions in the SAME LANGUAGE as the student uses.
    - Use the student's history to personalize your explanations.
    - If explaining a concept, reference specific parts of the course BY NAME (e.g. "The definition of Probability Space"), NOT by LaTeX reference codes (like \ref{...} or ???).
    - Be encouraging but precise.
    - Use LaTeX for match concepts. encase inline math with $...$ and block math with $$...$$.
    """
    
    # 2. Call Gemini
    if not api_key:
        yield "I am a mock chatbot. (API Key missing)"
        return
        
    try:
        model = genai.GenerativeModel('gemini-3-flash-preview')
        chat = model.start_chat(history=[])
        
        full_message = f"{system_prompt}\n\nStudent: {message}"
        response_stream = chat.send_message(full_message, stream=True)
        
        for chunk in response_stream:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        print(f"Chat Error: {e}")
        yield "Sorry, I'm having trouble thinking right now."
