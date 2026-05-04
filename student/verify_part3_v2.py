import requests
import json

BASE_URL = "http://localhost:8001"

def test_part3():
    print("--- Verifying Part III (Chatbot) ---")
    
    # Prerequisite: students exist
    res = requests.get(f"{BASE_URL}/api/students")
    students = res.json()
    if not students:
        print("No students found.")
        return
        
    sid = students[0]["id"]
    print(f"Chatting as {sid}...")
    
    msg = "Hello, can you help me with my weak points?"
    print(f"User: {msg}")
    
    res = requests.post(f"{BASE_URL}/api/chat", json={
        "student_id": sid,
        "message": msg,
        "history": []
    })
    
    if res.status_code == 200:
        print("Tutor Response:")
        print(res.json()["response"])
    else:
        print("Error:")
        print(res.text)

if __name__ == "__main__":
    test_part3()
