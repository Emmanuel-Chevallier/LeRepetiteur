import json
with open("data/courses/probabilites/grades.json") as f:
    d = json.load(f)
print("Grade in gradebook:", d.get("records", {}).get("0001", {}).get("4", {}))
