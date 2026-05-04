import requests

try:
    s = requests.get("http://localhost:8001/api/students").json()
    target = next((x for x in s if x["id"] == "0027"), None)
    if target:
        print(f"FOUND: {target}")
    else:
        print("NOT FOUND")
except Exception as e:
    print(e)
