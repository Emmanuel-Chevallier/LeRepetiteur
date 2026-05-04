import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "teacher"))

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import db

client = TestClient(app)

def test_duplicate_import():
    csv_content = """Nom;Prénom
    Dubois;Marie
    """
    files = {"file": ("test_dup.csv", csv_content, "text/csv")}
    
    # Import 1
    response = client.post("/api/students/import_csv", files={"file": ("test_dup.csv", csv_content, "text/csv")})
    print("Import 1:", response.json())
    
    # Import 2 (Duplicate)
    response = client.post("/api/students/import_csv", files={"file": ("test_dup.csv", csv_content, "text/csv")})
    print("Import 2:", response.json())
    
    # Import 3 (Duplicate again)
    response = client.post("/api/students/import_csv", files={"file": ("test_dup.csv", csv_content, "text/csv")})
    print("Import 3:", response.json())
    
    # Verify Names
    response = client.get("/api/students")
    students = response.json()
    last_three = students[-3:]
    
    print("--- Last 3 Students ---")
    for s in last_three:
        print(f"ID: {s['id']}, Last Name: {s['last_name']}, First Name: {s['first_name']}")

    # Clean up (we know we just added 3)
    for s in last_three:
        client.delete(f"/api/students/{s['id']}")
    print("Cleanup done")

if __name__ == "__main__":
    test_duplicate_import()
