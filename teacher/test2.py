from pathlib import Path
quiz_dir = Path(f"data/students/0001/probabilites/quiz_4")
correction_path = quiz_dir / "correction.json"
print("Exists:", correction_path.exists())
