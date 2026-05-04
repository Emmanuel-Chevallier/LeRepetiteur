
import sys
import json
# Add local site-packages to path if needed (e.g. for json_repair)
import site
site.main()

# Mock the text processing part of grader
def test_parsing():
    from json_repair import repair_json
    
    # CASE 1: Valid JSON
    text1 = '{"score": 10}'
    print(f"Test 1 (Valid): {json.loads(repair_json(text1))}")
    
    # CASE 2: Markdown block
    text2 = '```json\n{"score": 10}\n```'
    print(f"Test 2 (Markdown): {json.loads(repair_json(text2))}")
    
    # CASE 3: Broken JSON (missing quotes, trailing comma)
    text3 = '{score: 10,}'
    print(f"Test 3 (Broken): {json.loads(repair_json(text3))}")
    
    # CASE 4: The messy output we suspected
    text4 = """
    Here is the result:
    {
        "grades": [
            { "q": 1, "s": 5 } 
        ],
        "total": 5
    }
    Hope this helps.
    """
    print(f"Test 4 (Surrounded): {json.loads(repair_json(text4))}")

if __name__ == "__main__":
    try:
        test_parsing()
        print("✅ Parsing Tests Passed")
    except Exception as e:
        print(f"❌ Parsing Tests Failed: {e}")
