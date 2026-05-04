
import requests

BASE_URL = "http://localhost:8001"
TEST_ID = "9999"

def verify_student_management():
    print("--- Verifying Student Management (Anonymized) ---")
    
    # 1. Add Student (Valid)
    print(f"Adding Student #{TEST_ID}...")
    res = requests.post(f"{BASE_URL}/api/students", json={"id": TEST_ID})
    if res.ok:
        data = res.json()
        print(f"SUCCESS: Added {data['student']['name']}")
        if data['student']['id'] != TEST_ID:
            print("FAILURE: ID mismatch")
    else:
        print(f"FAILURE: {res.text}")
        
    # 2. Add Duplicate (Should Fail)
    print("Testing Duplicate...")
    res = requests.post(f"{BASE_URL}/api/students", json={"id": TEST_ID})
    if res.status_code == 400:
        print("SUCCESS: Duplicate rejected.")
    else:
        print(f"FAILURE: Duplicate allowed? {res.status_code}")
        
    # 3. Add Invalid ID (Should Fail)
    print("Testing Invalid ID 'abc'...")
    res = requests.post(f"{BASE_URL}/api/students", json={"id": "abc"})
    if res.status_code == 400:
        print("SUCCESS: Invalid ID rejected.")
    else:
        print(f"FAILURE: Invalid ID allowed? {res.status_code}")
        
    # 4. Check List
    print("Checking List...")
    students = requests.get(f"{BASE_URL}/api/students").json()
    found = any(s['id'] == TEST_ID for s in students)
    if found:
         print("SUCCESS: Student found in list.")
    else:
         print("FAILURE: Student NOT found in list.")
         
    # 5. Delete Student
    print(f"Deleting Student #{TEST_ID}...")
    res = requests.delete(f"{BASE_URL}/api/students/{TEST_ID}")
    if res.ok:
        print("SUCCESS: Deleted.")
    else:
        print(f"FAILURE: Delete failed {res.text}")
        
    # 6. Verify Gone
    students = requests.get(f"{BASE_URL}/api/students").json()
    found = any(s['id'] == TEST_ID for s in students)
    if not found:
         print("SUCCESS: Verified gone.")
    else:
         print("FAILURE: Student still exists.")

if __name__ == "__main__":
    verify_student_management()
