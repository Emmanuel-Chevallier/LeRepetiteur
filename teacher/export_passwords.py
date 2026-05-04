
import json
import csv
from pathlib import Path

def export_passwords():
    # Define paths
    base_dir = Path(__file__).parent
    data_file = base_dir / "data" / "global" / "students.json"
    output_file = base_dir / "students_passwords.csv"

    print(f"Reading from: {data_file}")
    
    if not data_file.exists():
        print("Error: Student data file not found.")
        return

    try:
        with open(data_file, "r") as f:
            students = json.load(f)
            
        # Write to CSV
        with open(output_file, "w", newline='') as csvfile:
            writer = csv.writer(csvfile)
            # Header
            writer.writerow(["ID Etudiant", "Mot de Passe"])
            
            # Data
            for s in students:
                writer.writerow([s.get("id", ""), s.get("password", "")])
                
        print(f"Successfully exported {len(students)} credentials to:")
        print(f" -> {output_file.resolve()}")
        
    except Exception as e:
        print(f"Error during export: {e}")

if __name__ == "__main__":
    export_passwords()
