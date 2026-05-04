import os
import google.generativeai as genai
from pathlib import Path

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    key_file = Path("Gemini_key")
    if key_file.exists():
        with open(key_file, "r") as f:
            api_key = f.read().strip()

if api_key:
    genai.configure(api_key=api_key)
    print("Listing models...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
else:
    print("No API Key found")
