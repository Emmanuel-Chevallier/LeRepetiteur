
import requests
import os

BASE_URL = "http://localhost:8001"

def verify_filename():
    print("--- Verifying Filename Preservation ---")
    
    # 1. Create Course
    cid = "FILENAME_TEST"
    print(f"Creating Course {cid}...")
    requests.post(f"{BASE_URL}/api/courses", json={"name": "Filename Test Course"})
    
    # Get ID properly this time (based on previous learning)
    res = requests.get(f"{BASE_URL}/api/courses")
    courses = res.json()
    course = next((c for c in courses if c["title"] == "Filename Test Course"), None)
    if not course:
        print("Failed to create course or find ID.")
        return
    cid_real = course["id"]
    print(f"Course ID: {cid_real}")

    # 2. Upload File with specific name
    unique_name = "my_custom_exam.tex"
    with open(unique_name, "w") as f:
        f.write("\\documentclass{article}\\begin{document}Hello\\end{document}")
        
    print(f"Uploading {unique_name}...")
    with open(unique_name, "rb") as f:
        res = requests.post(f"{BASE_URL}/api/courses/{cid_real}/upload", files={"file": f})
        print(f"Upload Result: {res.json()}")

    # 3. Verify File Exists on Disk
    expected_path = f"data/courses/{cid_real}/{unique_name}"
    if os.path.exists(expected_path):
        print(f"SUCCESS: File found at {expected_path}")
    else:
        print(f"FAILURE: File NOT found at {expected_path}")
        
    # 4. Verify DB Entry
    res = requests.get(f"{BASE_URL}/api/courses")
    updated_course = next((c for c in res.json() if c["id"] == cid_real), None)
    if updated_course and updated_course.get("latex_file_path") and unique_name in updated_course["latex_file_path"]:
         print(f"SUCCESS: DB updated correctly: {updated_course['latex_file_path']}")
    else:
         print(f"FAILURE: DB path incorrect: {updated_course.get('latex_file_path')}")

    # Cleanup
    os.remove(unique_name)

if __name__ == "__main__":
    verify_filename()
