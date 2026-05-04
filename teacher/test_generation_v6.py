
import os
import sys
from pathlib import Path
from backend.generator import generate_single_quiz, compile_global_pdf

# Mock Data
mock_student = {"id": "9999", "name": "Test Student"}
mock_course = {
    "id": "chem101", 
    "title": "Chemistry 101",
    "latex_file_path": "dummy.tex" # We need a dummy tex or valid path
}
mock_context = "This is a dummy context for the course."

def test_generation():
    print("Testing Single Quiz Generation...")
    
    # Ensure dummy tex exists if needed by generator logic (it checks existence)
    # Actually generator.py checks existence in generate_quizzes_for_course, but generate_single_quiz just takes context.
    # So we can skip file check if we call generate_single_quiz directly.
    
    # Set API KEY to avoid error if missing (generator handles it with mock content)
    # But let's check.
    
    quiz = generate_single_quiz(mock_student, mock_course, mock_context, 1)
    
    print(f"Quiz generated. Content length: {len(quiz['latex_content'])}")
    print(f"PDF Path: {quiz['pdf_path']}")
    
    if quiz['pdf_path'] and Path(quiz['pdf_path']).exists():
        print("✅ Single PDF Compiled Successfully.")
    else:
        print("❌ Single PDF Compilation Failed.")
        return

    print("\nTesting Global PDF Concatenation...")
    global_pdf = compile_global_pdf(mock_course, [quiz], 1)
    
    if global_pdf and Path(global_pdf).exists():
        print(f"✅ Global PDF Compiled Successfully: {global_pdf}")
    else:
        print("❌ Global PDF Compilation Failed.")

if __name__ == "__main__":
    # Fix path to allow imports
    sys.path.append(str(Path(__file__).parent))
    test_generation()
