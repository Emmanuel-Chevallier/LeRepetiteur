import requests
import json
from pathlib import Path
import os

BASE_URL = "http://localhost:8001"

def test_smart_grading():
    print("--- Verifying Smart Grading ---")
    
    # 1. Prerequisite: We need a Generated Quiz to exist in the DB (for matching) 
    # and a "fake" scan that matches its metadata.
    
    # Let's generate a new quiz to be sure.
    cid = "persistence_test_101" # Ensure this course exists from previous step
    res = requests.post(f"{BASE_URL}/api/courses/{cid}/generate")
    if res.status_code != 200:
        print("Failed to generate quiz. Is 'persistence_test_101' created and file uploaded?")
        # Creating course just in case
        requests.post(f"{BASE_URL}/api/courses", json={"name": "Smart Test"})
        # Upload file... assuming one exists. 
        # Actually, verifying previous steps might have left state.
        # Let's use "MATH_TEST_V2" which is more robust
        cid = "MATH_TEST_V2"
        res = requests.post(f"{BASE_URL}/api/courses/{cid}/generate")
        
    print(f"Generation response: {res.json()}")
    
    # 2. Extract Quiz Number dynamically
    try:
        quizzes = res.json().get("quizzes", [])
        if not quizzes:
             print("No quizzes returned.")
             return
        quiz_num = quizzes[0]["quiz_number"]
        print(f"Detected generated Quiz #{quiz_num}")
    except Exception as e:
        print(f"Error parsing quiz number: {e}")
        return

    # 3. Create Smart Scan
    scan_content = f"""
    EXAM HEADER
    Student: Alice Student
    Course: Math Test V2
    Quiz #{quiz_num}
    
    ANSWERS:
    1. The answer is 42.
    2. I think it is blue.
    """
    
    with open("smart_scan.txt", "w") as f:
        f.write(scan_content)
        
    print("Uploading Smart Scan...")
    with open("smart_scan.txt", "rb") as f:
        # Explicit filename and mime
        res = requests.post(f"{BASE_URL}/api/grading/smart", files={"file": ("smart_scan.txt", f, "text/plain")})
        
    print(json.dumps(res.json(), indent=2))

if __name__ == "__main__":
    test_smart_grading()
