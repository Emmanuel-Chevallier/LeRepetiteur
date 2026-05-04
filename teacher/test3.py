import json
from pathlib import Path

f = Path("data/courses/probabilites/grades.json")
with open(f) as fp:
    d = json.load(fp)

for s, qs in d.items():
    if not isinstance(qs, dict): continue
    for qn, qd in qs.items():
        if not isinstance(qd, dict): continue
        if qd.get("modified"):
            cfile = Path(f"data/students/{s}/probabilites/quiz_{qn}/correction.json")
            print(f"Student {s} Quiz {qn}: Modified. Checking {cfile}. Exists: {cfile.exists()}")
