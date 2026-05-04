
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
        {"id": "student_1", "name": "Alice Student"},
        {"id": "student_2", "name": "Bob Student"}
    ]
    with open(GLOBAL_DIR / "students.json", "w") as f:
        json.dump(students, f, indent=2)
    print("Reset students.json (Alice & Bob preserved)")

    # Courses: Empty list
    with open(GLOBAL_DIR / "courses.json", "w") as f:
        json.dump([], f, indent=2)
    print("Reset courses.json to empty list")

    # Quizzes: Empty list
    with open(GLOBAL_DIR / "quizzes.json", "w") as f:
        json.dump([], f, indent=2)
    print("Reset quizzes.json to empty list")

    # 2. Clear Directories
    # Clear data/courses/*
    if COURSES_DIR.exists():
        shutil.rmtree(COURSES_DIR)
        COURSES_DIR.mkdir()
        print("Cleared data/courses/")
    
    # Clear data/students/* (removes all quiz folders and student folders)
    if STUDENTS_DIR.exists():
        shutil.rmtree(STUDENTS_DIR)
        STUDENTS_DIR.mkdir()
        # Re-create student folders for Alice and Bob? Not strictly necessary until they do something, 
        # but good for consistency if the app expects them.
        (STUDENTS_DIR / "student_1").mkdir()
        (STUDENTS_DIR / "student_2").mkdir()
        print("Cleared data/students/ and re-created folders for student_1 and student_2")

    # Clear temp
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
        TEMP_DIR.mkdir()
        print("Cleared data/temp/")

    print("Data reset complete.")

if __name__ == "__main__":
    reset_data()
