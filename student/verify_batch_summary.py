
import requests
import json
import time

BASE_URL = "http://localhost:8001"

def verify_batch_cycle():
    print("--- Verifying Batch & Summary ---")
    
    print(f"Creating Course...")
    res = requests.post(f"{BASE_URL}/api/courses", json={"name": "Batch Test Course"})
    data = res.json()
    print(f"DEBUG: Response keys: {data.keys()}")
    cid = data["course"]["id"]
    print(f"Created Course ID: {cid}")
    
    # Enroll Alice and Bob (student_1, student_2)
    requests.post(f"{BASE_URL}/api/courses/{cid}/enrollments", json={"student_ids": ["student_1", "student_2"]})
    
    # 2. Generate Quiz (Quiz #1 likely)
    print("Generating Quizzes...")
    # Upload dummy source
    with open("dummy_source.tex", "rb") as f: # Use dummy source
        requests.post(f"{BASE_URL}/api/courses/{cid}/upload", files={"file": f})
        
    res = requests.post(f"{BASE_URL}/api/courses/{cid}/generate")
    print(f"Gen Result: {res.json()}")
    
    try:
        quiz_num = res.json()["quizzes"][0]["quiz_number"]
        print(f"Quiz #{quiz_num} generated.")
    except:
        print("Failed to get quiz number.")
        return

    # 3. Simulate Batch Upload (2 scans)
    # Scan 1: Alice
    scan_1 = f"""
    App Header
    Student: Alice Student
    Course: Batch Test Course
    Quiz #{quiz_num}
    
    My Answer: I understand everything about Concept 1.
    """
    # Scan 2: Bob
    scan_2 = f"""
    App Header
    Student: Bob Student
    Course: Batch Test Course
    Quiz #{quiz_num}
    
    My Answer: I am confused about Concept 1.
    """
    
    files = [
        ("alice_scan.txt", scan_1),
        ("bob_scan.txt", scan_2)
    ]
    
    print("Simulating Batch Uploads (Smart Grade)...")
    
    for fname, content in files:
        print(f"Uploading {fname}...")
        with open(fname, "w") as f:
            f.write(content)
            
        with open(fname, "rb") as f:
            # Force mime text/plain
            res = requests.post(f"{BASE_URL}/api/grading/smart", files={"file": (fname, f, "text/plain")})
            print(f"Grade Result: {res.json()}")
            
    # 4. Trigger Summary
    print("Triggering Global Summary...")
    res = requests.post(f"{BASE_URL}/api/courses/{cid}/quizzes/{quiz_num}/summary")
    try:
        print(f"Summary Result: {json.dumps(res.json(), indent=2)}")
    except:
        print(f"Summary Failed to parse JSON. Status: {res.status_code}. Text: {res.text}")
    
    if res.ok:
        print("SUCCESS: Summary generated.")
    else:
        print("FAILURE: Summary failed.")

if __name__ == "__main__":
    verify_batch_cycle()
