import requests
import json
import time

BASE_URL = "http://localhost:8001"

def test_part1():
    print("--- Verifying Part I (V2) ---")
    
    # 1. Create Course
    cid = "MATH_TEST_V2"
    print(f"Creating Course {cid}...")
    res = requests.post(f"{BASE_URL}/api/courses", json={"id": cid, "title": "Math Test V2"})
    print(res.json())

    # 2. Upload File (Create a dummy tex file)
    with open("dummy.tex", "w") as f:
        f.write("\n".join([f"Line {i}: Concept {i}" for i in range(100)]))
    
    print("Uploading file...")
    with open("dummy.tex", "rb") as f:
        res = requests.post(f"{BASE_URL}/api/courses/{cid}/upload", files={"file": f})
    print(res.json())

    # 3. Set Settings
    print("Setting progress to line 10...")
    res = requests.post(f"{BASE_URL}/api/courses/{cid}/settings", json={
        "last_covered_line": 10,
        "custom_prompt": "Ask about even numbers only."
    })
    print(res.json())

    # 4. Generate
    print("Generating quizzes...")
    res = requests.post(f"{BASE_URL}/api/courses/{cid}/generate")
    if res.status_code == 200:
        data = res.json()
        print(f"Success: {data['message']}")
        print(f"Quizzes Generated: {len(data['quizzes'])}")
        if len(data['quizzes']) > 0:
            print("Sample Quiz Content:")
            print(data['quizzes'][0]['latex_content'][:200])
    else:
        print(f"Error: {res.text}")

if __name__ == "__main__":
    test_part1()
