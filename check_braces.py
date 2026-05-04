import re

js_path = 'teacher/frontend/debug_script.js'

with open(js_path, 'r') as f:
    js_content = f.read()

stack = []
for i, char in enumerate(js_content):
    if char == '{':
        stack.append(i)
    elif char == '}':
        if not stack:
            print(f"Error: Unmatched closing brace '}}' at index {i}")
            # print context
            start = max(0, i-50)
            end = min(len(js_content), i+50)
            print(f"Context: ...{js_content[start:end]}...")
        else:
            stack.pop()

if stack:
    print(f"Error: {len(stack)} unmatched opening braces '{{'")
    for idx in stack[-5:]: # Show last 5
        print(f"Unmatched '{{' at index {idx}")
        start = max(0, idx-50)
        end = min(len(js_content), idx+50)
        print(f"Context: ...{js_content[start:end]}...")
else:
    print("Brace check passed!")
