import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "teacher"))

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import db

client = TestClient(app)

def test_routes():
    # Test CSV Import
    csv_content = """Nom;Prénom
Baudelaire;Charles
Hugo;Victor
"""
    files = {"file": ("test.csv", csv_content, "text/csv")}
    response = client.post("/api/students/import_csv", files=files)
    print("--- Import CSV ---")
    print("Status:", response.status_code)
    print("JSON:", response.json())
    
    # Check students list
    response = client.get("/api/students")
    students = response.json()
    print("--- Students List after import (last 2) ---")
    print(students[-2:])
    
    # Edit the last student
    last_student = students[-1]
    sid = last_student["id"]
    payload = {"first_name": "Jean", "last_name": "Valjean"}
    response = client.patch(f"/api/students/{sid}", json=payload)
    print("--- Edit Student ---")
    print("Status:", response.status_code)
    print("JSON:", response.json())
    
    # Check students list again
    response = client.get("/api/students")
    students = response.json()
    print("--- Students List after edit ---")
    print(students[-1])
    
    # Let's delete them to clean up
    client.delete(f"/api/students/{students[-2]['id']}")
    client.delete(f"/api/students/{students[-1]['id']}")
    print("--- Cleanup Done ---")

if __name__ == "__main__":
    test_routes()
