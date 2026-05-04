import requests

try:
    print("Testing Password Generation Endpoint...")
    res = requests.post("http://localhost:8001/api/students/passwords/generate")
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.text}")
except Exception as e:
    print(f"Error: {e}")
