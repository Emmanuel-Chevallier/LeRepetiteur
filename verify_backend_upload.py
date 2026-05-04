import requests
import os

def test_upload():
    url = "http://localhost:8001/api/grading/smart"
    file_path = "dummy.pdf"
    
    # Ensure dummy.pdf exists
    if not os.path.exists(file_path):
        with open(file_path, "wb") as f:
            f.write(b"%PDF-1.4 empty pdf")
            
    with open(file_path, "rb") as f:
        files = {"file": f}
        data = {
            "is_bulk": "true",
            "override_quiz_number": "2",
            "include_context": "false"
        }
        
        print("Sending POST request to", url)
        try:
            with requests.post(url, files=files, data=data, stream=True) as r:
                print(f"Response Status: {r.status_code}")
                if r.status_code != 200:
                    print("Error Content:", r.text)
                    return
                print("Headers:", r.headers)
                
                print("--- Stream Content ---")
                for line in r.iter_lines():
                    if line:
                        print(line.decode('utf-8'))
                print("--- End Stream ---")
                
        except Exception as e:
            print(f"Request Failed: {e}")

if __name__ == "__main__":
    test_upload()
