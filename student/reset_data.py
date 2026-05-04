
import json
import shutil
import os
from pathlib import Path

DATA_DIR = Path("data")
GLOBAL_DIR = DATA_DIR / "global"
COURSES_DIR = DATA_DIR / "courses"
STUDENTS_DIR = DATA_DIR / "students"
TEMP_DIR = DATA_DIR / "temp"

def reset_data():
    print("Resetting data...")

    # 1. Reset Global Files
    # Students: Alice and Bob
    students = [
        {"id": "student_1", "name": "Alice Student", "password": "password"},
        {"id": "student_2", "name": "Bob Student", "password": "password"}
    ]
    with open(GLOBAL_DIR / "students.json", "w") as f:
        json.dump(students, f, indent=2)
    print("Reset students.json with passwords")

    # Courses: Math 101
    courses = [
        {
            "id": "math101",
            "title": "Introduction aux Probabilités",
            "teacher_id": "prof_admin",
            "enrolled_students": ["student_1", "student_2"]
        }
    ]
    with open(GLOBAL_DIR / "courses.json", "w") as f:
        json.dump(courses, f, indent=2)
    print("Reset courses.json with Math 101")

    # Quizzes: Empty registry (or dummy if needed by grader, but history is enough for viewer)
    with open(GLOBAL_DIR / "quizzes.json", "w") as f:
        json.dump([], f, indent=2)
    
    # 2. Clear Directories
    if COURSES_DIR.exists(): shutil.rmtree(COURSES_DIR)
    COURSES_DIR.mkdir()
    (COURSES_DIR / "math101").mkdir()
    
    if STUDENTS_DIR.exists(): shutil.rmtree(STUDENTS_DIR)
    STUDENTS_DIR.mkdir()
    
    # 3. Create Alice's History with a dummy quiz
    (STUDENTS_DIR / "student_1").mkdir()
    alice_history = {
        "weak_concepts": ["Théorème de Bayes"],
        "past_quizzes": [
            {
                "quiz_number": 1,
                "course_id": "math101",
                "scan_url": "", 
                "correction": {
                    "total_score": 12,
                    "grades": [
                        {
                            "question_number": 1,
                            "score": 2,
                            "transcription": "P(A|B) = P(B|A) * P(A)",
                            "feedback": "C'est presque ça, mais il manque le dénominateur P(B). La formule de Bayes est P(A|B) = P(B|A) * P(A) / P(B)."
                        },
                        {
                            "question_number": 2,
                            "score": 10,
                            "transcription": "L'événement est certain si sa probabilité vaut 1.",
                            "feedback": "Correct. Bonne définition."
                        }
                    ]
                }
            }
        ]
    }
    with open(STUDENTS_DIR / "student_1" / "history.json", "w") as f:
        json.dump(alice_history, f, indent=2)

    (STUDENTS_DIR / "student_2").mkdir()  # Bob empty

    print("Data reset complete. Alice has 1 quiz in Math 101.")

if __name__ == "__main__":
    reset_data()
