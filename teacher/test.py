from pathlib import Path
import json

p = Path("data/courses/probabilites/grades.json")
with open(p) as f:
    print(json.load(f))
