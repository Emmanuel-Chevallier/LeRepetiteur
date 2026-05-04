import requests

res = requests.post("http://localhost:8005/api/courses/probabilites/grades", json={
    "student_id": "0001",
    "quiz_number": 4,
    "score": 3
})
print("Status Code:", res.status_code)
print("Response:", res.text)
