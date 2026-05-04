
import requests
import time

BASE_URL = "http://localhost:8001"

def verify_interval():
    print("--- Verifying Content Interval ---")
    
    # 1. Create Course
    print("Creating Internal Test Course...")
    res = requests.post(f"{BASE_URL}/api/courses", json={"name": "Interval Test"})
    data = res.json()
    # Depending on endpoint implementation, create might return {"message":..., "course": {...}} or just {...}
    # Checking main.py: @app.post("/api/courses") -> return course (dict) directly?
    # Let's check main.py line 40?
    if "id" in data:
        cid = data["id"]
    elif "course" in data:
        cid = data["course"]["id"]
    else:
        print(f"Unknown response format: {data}")
        return
    
    # 2. Upload Dummy File (100 lines)
    print("Uploading 100-line file...")
    lines = [f"Line {i} content." for i in range(100)]
    content = "\n".join(lines)
    
    with open("interval_source.tex", "w") as f:
        f.write(content)
        
    with open("interval_source.tex", "rb") as f:
        requests.post(f"{BASE_URL}/api/courses/{cid}/upload", files={"file": f})
        
    # 3. Set Interval (20 to 30)
    print("Setting Interval 20-30...")
    requests.post(f"{BASE_URL}/api/courses/{cid}/settings", json={
        "start_line": 20,
        "end_line": 30,
        "custom_prompt": "Test Interval"
    })
    
    # 4. Trigger Generation
    # We can't easily see the internal print stdout here, but we can check if it runs without error.
    # Ideally, we would inspect the generated prompt or logs, but for now we rely on the implementation correctness + server log inspection if needed.
    print("Triggering Generation...")
    res = requests.post(f"{BASE_URL}/api/courses/{cid}/generate")
    if res.ok:
        print(f"Generation OK: {res.json()}")
    else:
        print(f"Generation Failed: {res.text}")

if __name__ == "__main__":
    verify_interval()
