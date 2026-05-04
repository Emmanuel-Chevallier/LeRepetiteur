import os
import json
import google.generativeai as genai
from pathlib import Path
from typing import Dict, Any, Optional

# Re-configure API if needed (usually main.py does it, but good to be safe)
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    key_file = Path(__file__).parent.parent / "Gemini_key"
    if key_file.exists():
        with open(key_file, "r") as f:
            api_key = f.read().strip()

if api_key:
    genai.configure(api_key=api_key)

from pypdf import PdfReader, PdfWriter

def split_pdf(file_path: Path, pages_per_chunk: int) -> list[Path]:
    """Splits a PDF into chunks of pages_per_chunk."""
    chunks = []
    try:
        reader = PdfReader(file_path)
        total_pages = len(reader.pages)
        
        base_name = file_path.stem
        output_dir = file_path.parent / "chunks" / base_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for i in range(0, total_pages, pages_per_chunk):
            writer = PdfWriter()
            end = min(i + pages_per_chunk, total_pages)
            for page_num in range(i, end):
                writer.add_page(reader.pages[page_num])
            
            chunk_name = f"{base_name}_part_{i//pages_per_chunk + 1}.pdf"
            chunk_path = output_dir / chunk_name
            with open(chunk_path, "wb") as f:
                writer.write(f)
            chunks.append(chunk_path)
    except Exception as e:
        print(f"Error splitting PDF: {e}")
        # Fallback: return original if split fails
        return [file_path]
    return chunks

def analyze_single_chunk(chunk_path: Path, default_quiz_number: int = None) -> Dict[str, Any]:
    """Analyzes a single PDF chunk."""
    try:
        # Upload to Gemini
        sample_file = genai.upload_file(path=chunk_path, display_name=chunk_path.name)
        
        # Prompt
        prompt = """
        Analyze this scanned student exam header. Extract:
        - student_id (integer or string)
        - quiz_number (integer)
        - course_title (string, ONLY if explicitly written in the header. Do NOT guess from context.)
        - confidence (high/medium/low)

        Return JSON only:
        {
          "student_id": "...",
          "quiz_number": 123,
          "course_title": "...",
          "confidence": "high"
        }
        """
        
        model = genai.GenerativeModel(model_name="gemini-3-flash-preview")
        response = model.generate_content([sample_file, prompt])
        text = response.text.strip()
        
        # Cleanup JSON
        if text.startswith("```json"):
            text = text[7:-3]
        elif text.startswith("```"):
            text = text[3:-3]
            
        import json_repair
        data = json_repair.loads(text)
        
        # --- Default Logic ---
        data["detected_quiz_number"] = data.get("quiz_number")
        
        if default_quiz_number is not None:
             if not data.get("quiz_number"):
                data["quiz_number"] = default_quiz_number

        return {
            "file_id": chunk_path.name,
            "student_id": data.get("student_id"),
            "quiz_number": data.get("quiz_number"),
            "detected_quiz_number": data.get("detected_quiz_number"),
            "course_title": data.get("course_title"),
            "confidence": data.get("confidence", "low"),
            "raw_text": text 
        }
        
    except Exception as e:
        print(f"Error analyzing chunk {chunk_path}: {e}")
        return {"file_id": chunk_path.name, "error": str(e)}

def analyze_header(file_path: Path, pages_per_copy: int = 2, default_quiz_number: int = None) -> list[Dict[str, Any]]:
    """
    Analyzes the header of a scanned document.
    If PDF and > pages_per_copy, splits it first.
    Returns a list of results.
    """
    if not api_key:
        return [{"error": "No API Key found"}]

    model_name = "gemini-3-flash-preview"
    results = []

    # 1. Determine files to process
    files_to_process = []
    if file_path.suffix.lower() == ".pdf":
        files_to_process = split_pdf(file_path, pages_per_copy)
    else:
        files_to_process = [file_path]
        
    print(f"DEBUG: Processing {len(files_to_process)} chunks from {file_path}")
    
    results = []
    
    for chunk in files_to_process:
        res = analyze_single_chunk(chunk, default_quiz_number)
        results.append(res)
        
    return results
