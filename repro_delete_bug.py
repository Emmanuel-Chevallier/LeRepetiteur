import requests
import time

BASE_URL = "http://localhost:8001/api"

def test_delete():
    # 1. Create Student
    print("Creating Student 8888...")
    res = requests.post(f"{BASE_URL}/students", json={"id": "8888"})
    print("Create:", res.status_code)
    
    # 2. Verify existence
    students = requests.get(f"{BASE_URL}/students").json()
    exists = any(s['id'] == "8888" for s in students)
    print(f"Student 8888 exists: {exists}")
    
    if not exists:
        print("Setup failed.")
        return

    # 3. Delete
    print("Deleting Student 8888...")
    res = requests.delete(f"{BASE_URL}/students/8888")
    print("Delete Response:", res.status_code, res.text)
    
    # 4. Verify removal
    students = requests.get(f"{BASE_URL}/students").json()
    still_exists = any(s['id'] == "8888" for s in students)
    print(f"Student 8888 still exists: {still_exists}")

if __name__ == "__main__":
    test_delete()
