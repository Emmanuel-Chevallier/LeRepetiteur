
import requests

BASE_URL = "http://localhost:8001"

def verify_server_up():
    print("--- Checking Server ---")
    try:
        res = requests.get(BASE_URL)
        if res.status_code == 200:
            print("Server is UP and serving index.html")
            if "handleFiles" in res.text or "addToQueue" in res.text:
                 print("Index.html contains new JS logic.")
            else:
                 print("WARNING: Index.html might not be updated?")
        else:
            print(f"Server returned {res.status_code}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    verify_server_up()
