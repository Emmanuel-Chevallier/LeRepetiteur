import requests
import os

def test_upload():
    url = "http://localhost:8001/api/grading/smart"
    file_path = "teacher/bulk_test.pdf"
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
            
    with open(file_path, "rb") as f:
        files = {"file": f}
        data = {
            "is_bulk": "true",
            "override_quiz_number": "2",
            "override_course_id": "probabilites",
            "include_context": "false"
        }
        
        print("Sending POST request to", url)
        try:
            with requests.post(url, files=files, data=data, stream=True, timeout=600) as r:
                print(f"Response Status: {r.status_code}")
                if r.status_code != 200:
                    print("Error Content:", r.text)
                    return
                print("Headers:", r.headers)
                
                print("--- Stream Content ---")
                count = 0
                for line in r.iter_lines():
                    if line:
                        print(f"Line {count}: {line.decode('utf-8')}", flush=True)
                        count += 1
                print("--- End Stream ---")
                
        except Exception as e:
            print(f"Request Failed: {e}")

if __name__ == "__main__":
    test_upload()
