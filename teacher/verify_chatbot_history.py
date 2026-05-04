
import os
import sys
# Ensure backend importable
sys.path.append(os.getcwd())

from backend.database import db
from backend.chatbot import get_chat_response
from typing import List, Dict

# Mock the database/crawling part by running it directly if we can't easily import internal logic
# Actually get_chat_response does the crawling itself now.
# We just need to call it and see if it finds context.
# We'll use student "0001" and course "proba" which we know have files.

def test_chatbot_context():
    student_id = "0001"
    course_id = "proba"
    message = "Which quizzes have I taken?"
    
    # We will temporarily print the prompt that is generated, 
    # but we can't easily see internal variables of the function.
    # However, get_chat_response calls genai. 
    # We can mock genai to capture the prompt.
    
    import google.generativeai as genai
    
    original_model = genai.GenerativeModel
    
    class MockChat:
        def send_message(self, content):
            print("\n--- CAPTURED PROMPT ---")
            print(content)
            print("-----------------------\n")
            return type('obj', (object,), {'text': "Mock Response"})()
            
    class MockModel:
        def __init__(self, model_name): pass
        def start_chat(self, history=[]): return MockChat()
        
    genai.GenerativeModel = MockModel
    
    print(f"Testing Chatbot for Student {student_id}, Course {course_id}...")
    try:
        get_chat_response(student_id, message, [], course_id)
        print("✅ Called successfully.")
    except Exception as e:
        print(f"❌ Failed: {e}")
    finally:
        genai.GenerativeModel = original_model

if __name__ == "__main__":
    test_chatbot_context()
