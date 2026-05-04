import re

def remove_comments_and_strings(content):
    # Remove strings
    pattern_str = r'(["\'])(?:(?=(\\?))\2.)*?\1'
    content = re.sub(pattern_str, '""', content)
    # Remove template literals (rough approximation, handles simple cases)
    content = re.sub(r'`[^`]*`', '``', content)
    # Remove single line comments
    content = re.sub(r'//.*', '', content)
    # Remove multi-line comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    return content

js_path = 'teacher/frontend/debug_script.js'

try:
    with open(js_path, 'r') as f:
        original_content = f.read()

    clean_content = remove_comments_and_strings(original_content)

    stack = []
    lines = clean_content.split('\n')
    
    # We need to track original indices for error reporting? 
    # Hard after stripping. Let's just scan the cleaned string but keep newlines for line numbers.
    
    current_line = 1
    for char in clean_content:
        if char == '\n':
            current_line += 1
        elif char == '{':
            stack.append(current_line)
        elif char == '}':
            if not stack:
                print(f"Error: Unmatched '}}' at line {current_line}")
                exit(1)
            else:
                stack.pop()

    if stack:
        print(f"Error: Unmatched '{{' at line {stack[-1]} (Total unmatched: {len(stack)})")
    else:
        print("Syntax (Braces) OK.")

except FileNotFoundError:
    print("File not found.")
