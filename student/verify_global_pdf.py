
import requests
import os

BASE_URL = "http://localhost:8001"

def verify_global_pdf():
    print("--- Verifying Global PDF ---")
    
    # 1. Upload & Generate (Use existing Interval Test course if possible, or new)
    # Reset is expensive, let's just make a new course "GlobalPDF Test"
    print("Creating Course...")
    res = requests.post(f"{BASE_URL}/api/courses", json={"name": "GlobalPDF Test"})
    if not res.ok:
        print("Failed to create course or already exists. proceeding...")
        # Try to find ID
        courses = requests.get(f"{BASE_URL}/api/courses").json()
        cid = next((c["id"] for c in courses if c["title"] == "GlobalPDF Test" or c["id"] == "globalpdf_test"), "globalpdf_test")
    else:
        # Parsing ID logic
        data = res.json()
        cid = data.get("id") or data.get("course", {}).get("id")
        
    print(f"Course ID: {cid}")
    
    # 2. Upload Dummy File
    content = "Line 1\nLine 2\nLine 3"
    with open("mini_source.tex", "w") as f:
        f.write(content)
        
    with open("mini_source.tex", "rb") as f:
        requests.post(f"{BASE_URL}/api/courses/{cid}/upload", files={"file": f})
        
    # 3. Generate
    print("Generating Quizzes...")
    requests.post(f"{BASE_URL}/api/courses/{cid}/generate")
    
    # 4. Check File Existence
    # We expect data/courses/{cid}/all_quizzes_1.pdf
    # We need to find the quiz number. 
    # Let's assume it's 1 since new course.
    expected_path = f"data/courses/{cid}/all_quizzes_1.pdf"
    
    if os.path.exists(expected_path):
        print(f"SUCCESS: {expected_path} found.")
    else:
        print(f"FAILURE: {expected_path} NOT found.")
        # Check logic: if course already existed, quiz num might be higher.
        # Check dir
        print(f"Contents of data/courses/{cid}:")
        os.system(f"ls -l data/courses/{cid}")

if __name__ == "__main__":
    verify_global_pdf()
