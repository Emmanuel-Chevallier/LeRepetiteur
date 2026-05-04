
import requests
import json

BASE_URL = "http://localhost:8001"
COURSE_ID = "gradebook_test"

def verify_gradebook():
    print("--- Verifying Gradebook ---")
    
    # 1. Create Course
    print("Creating internal test course...")
    requests.post(f"{BASE_URL}/api/courses", json={"name": "Gradebook Test"})
    # ID manual assumption: 'gradebook_test'
    cid = "gradebook_test"
    
    # 2. Simulate Auto-Grading (we assume grading system works, but we also manually call backend/grader equivalent if we could, 
    # but here we can only call API or trust previous steps. 
    # Actually, we can assume the course has students, but it doesn't default.
    # Enrolling is needed for gradebook display iteration, BUT gradebook stores IDs encountered in records too.
    # Let's verify empty first.
    
    res = requests.get(f"{BASE_URL}/api/courses/{cid}/grades")
    print(f"Empty Gradebook: {res.json()}")
    
    # 3. Manually Update a Grade (Simulate Edit directly via API)
    # Allows creating a grade for a student even if not enrolled in list? Yes, logic handles it.
    print("Updating grade for Student A, Quiz 1...")
    requests.post(f"{BASE_URL}/api/courses/{cid}/grades", json={
        "student_id": "student_A",
        "quiz_number": 1,
        "score": 14.5
    })
    
    # 4. Fetch and Verify
    res = requests.get(f"{BASE_URL}/api/courses/{cid}/grades")
    data = res.json()
    print("Updated Gradebook:", json.dumps(data, indent=2))
    
    student_row = next((s for s in data["students"] if s["student_id"] == "student_A"), None)
    if student_row:
        grade = student_row["grades"].get("1")
        if grade and grade["score"] == 14.5 and grade["modified"] == True:
            print("SUCCESS: Grade updated and marked modified.")
        else:
            print(f"FAILURE: Data mismatch. {grade}")
    else:
        print("FAILURE: Student row not found.")

if __name__ == "__main__":
    verify_gradebook()
