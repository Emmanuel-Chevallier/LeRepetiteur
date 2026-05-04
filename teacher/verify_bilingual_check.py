
import os
import sys
import json
sys.path.append(os.getcwd())

from backend import generator, grader
from backend.database import db

# Use verify mode
# We will inspect the PROMPT that is generated, to avoid wasting tokens on full generation if possible,
# OR generate a small request.

def verify_generator_prompt():
    print("--- Verifying Generator Prompt ---")
    
    # Check file content directly
    fname = "backend/generator.py"
    if not os.path.exists(fname):
        print(f"❌ {fname} missing")
        return

    # We can't access `prompt` local variable easily.
    # But `generate_quiz` calls `genai`.
    # Let's inspect `backend/generator.py` content to see if my edit stuck.
    # Or just trust the `replace_file_content` if it succeeded (it did).
    # Let's try to actually GENERATE a small dummy quiz?  
    # That might be slow/expensive.
    # Better: Inspect the file content via python to ensure the string is there.
    
    with open("backend/generator.py", "r") as f:
        content = f.read()
        if "IMPORTANT: All questions must be BILINGUAL" in content:
            print("✅ Generator: Bilingual Instruction FOUND.")
        else:
            print("❌ Generator: Bilingual Instruction NOT FOUND.")
            
    with open("backend/grader.py", "r") as f:
        content = f.read()
        if "Feedback & Weak Points in BILINGUAL FORMAT" in content:
            print("✅ Grader: Bilingual Instruction FOUND.")
        else:
            print("❌ Grader: Bilingual Instruction NOT FOUND.")

if __name__ == "__main__":
    verify_generator_prompt()
