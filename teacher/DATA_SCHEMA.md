# Data Storage Schema (JSON)

## 1. Global Data (`data/global/`)

### `students.json`
List of all students available in the system.
```json
[
  {
    "id": "student_123",
    "name": "Alice Dupont",
    "email": "alice@example.com",
    "password_hash": "...",
    "role": "student"
  }
]
```

### `courses.json`
List of courses and their metadata.
```json
[
  {
    "id": "math101",
    "title": "Mathematics 101",
    "teacher_id": "prof_smith",
    "latex_file_path": "data/courses/math101/source.tex",
    "last_covered_line": 150,
    "custom_prompt": "Focus on definitions.",
    "enrolled_students": ["student_123", "student_456"]
  }
]
```

## 2. Course Data (`data/courses/{course_id}/`)
- `source.tex`: Original LaTeX file.
- `generated_quizzes/`: Folder containing generated PDFs.

## 3. Student Data (`data/students/{student_id}/`)
Detailed records for each student.

### `history.json`
Tracks performance and weak points.
```json
{
  "weak_concepts": ["derivatives", "limits"],
  "past_quizzes": [
    {
      "quiz_id": "quiz_math101_2025_01_01",
      "course_id": "math101",
      "score": 14.5,
      "max_score": 20,
      "transcript_path": "data/students/student_123/quiz_math101_2025_01_01_transcript.tex",
      "scan_path": "data/students/student_123/quiz_math101_2025_01_01_scan.pdf",
      "feedback": "..."
    }
  ]
}
```

## 4. Quizzes Registry (`data/quizzes.json`)
To map quiz IDs to their content (needed for grading).
```json
[
  {
    "id": "quiz_math101_2025_01_01",
    "course_id": "math101",
    "student_id": "student_123",
    "latex_content": "...",
    "correction_guide": "..." 
  }
]
```
