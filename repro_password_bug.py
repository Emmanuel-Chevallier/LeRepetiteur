import requests
import time

BASE_URL = "http://localhost:8001/api"

def test_flow():
    # 1. Create Student
    print("Creating Student 9999...")
    res = requests.post(f"{BASE_URL}/students", json={"id": "9999"})
    print("Create:", res.status_code, res.text)
    
    # 2. Check if exists and has no password
    students = requests.get(f"{BASE_URL}/students").json()
    s = next((x for x in students if x["id"] == "9999"), None)
    if not s:
        print("ERROR: Student not found!")
        return
    print(f"Student State: password={s.get('password')}")

    # 3. Generate Passwords
    print("Generating Passwords...")
    res = requests.post(f"{BASE_URL}/students/passwords/generate")
    print("Generate:", res.status_code, res.json()['message'])
    
    # 4. Verify
    students = requests.get(f"{BASE_URL}/students").json()
    s = next((x for x in students if x["id"] == "9999"), None)
    print(f"Final State: password={s.get('password')}")
    
    # Cleanup
    requests.delete(f"{BASE_URL}/students/9999")

if __name__ == "__main__":
    test_flow()
