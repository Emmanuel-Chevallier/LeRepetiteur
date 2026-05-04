import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8001"

def test_part2():
    print("--- Verifying Part II (V2 Grading) ---")
    
    # Prerequisite: verify_part1_v2 must have run (created course/quizzes)
    # Course: MATH_TEST_V2
    # Student: we probably need to find a valid student.
    
    # 1. Fetch Students
    res = requests.get(f"{BASE_URL}/api/students")
    students = res.json()
    if not students:
        print("No students found. Run verify_part1_v2 first or wait for init.")
        return
    
    sid = students[0]["id"]
    cid = "MATH_TEST_V2"
    
    print(f"Grading for Student: {sid}, Course: {cid}")
    
    # 2. Create Dummy Scan (Text file pretending to be PDF/Image)
    # In real life this would be a PDF/image.
    with open("dummy_scan.txt", "w") as f:
        f.write("Answer 1: The derivative of x^2 is 2x.\nAnswer 2: I don't know.")
        
    print("Uploading Scan...")
    with open("dummy_scan.txt", "rb") as f:
        # Note: server expects 'file', query params student_id, course_id
        res = requests.post(f"{BASE_URL}/api/grading/upload", 
                          params={"student_id": sid, "course_id": cid},
                          files={"file": f})
                          
    if res.status_code == 200:
        print("Success!")
        print(json.dumps(res.json(), indent=2))
    else:
        print("Error:")
        print(res.text)

if __name__ == "__main__":
    test_part2()
