import requests
import json
import os

BASE_URL = "http://localhost:8001/api"
SID = "0027"

def debug_deletion():
    print(f"--- Debugging Deletion of Student {SID} ---")
    
    # 1. Check DB
    try:
        students = requests.get(f"{BASE_URL}/students").json()
        student = next((s for s in students if s["id"] == SID), None)
        if student:
            print(f"Student found in DB: {student}")
        else:
            print("Student NOT found in DB.")
            return
    except Exception as e:
        print(f"Error checking DB: {e}")
        return

    # 2. Check Filesystem (Simulated checks via Python direct access not allowed remotely, but tool works locally)
    # We are running this on the server effectively.
    stud_dir = f"teacher/data/students/{SID}"
    if os.path.exists(stud_dir):
        print(f"Directory {stud_dir} exists.")
        print(f"Contents: {os.listdir(stud_dir)}")
    else:
        print(f"Directory {stud_dir} does NOT exist.")

    # 3. Attempt Delete
    print("Sending DELETE request...")
    res = requests.delete(f"{BASE_URL}/students/{SID}")
    print(f"Status: {res.status_code}")
    print(f"Response: {res.text}")

if __name__ == "__main__":
    debug_deletion()
