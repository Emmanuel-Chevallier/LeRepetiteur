
import re

def check_syntax(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()

    # Extract script content
    script_lines = []
    in_script = False
    start_line = 0
    
    for i, line in enumerate(lines):
        if '<script>' in line:
            in_script = True
            start_line = i + 1
            script_lines.append("") # Keep line numbers aligned
            continue
        if '</script>' in line:
            in_script = False
        
        if in_script:
            script_lines.append(line)
        else:
            script_lines.append("") # Empty lines for outside script

    content = "".join(script_lines)
    
    # helper to find mismatches
    stack = []
    mapping = {')': '(', ']': '[', '}': '{'}
    reverse_mapping = {v: k for k, v in mapping.items()}
    
    # Remove comments (simple regex, not perfect but helps)
    # Block comments
    content_no_comments = re.sub(r'/\*.*?\*/', lambda m: ' ' * len(m.group(0)), content, flags=re.DOTALL)
    # Line comments (careful with URLs etc, but let's try)
    lines_no_comments = []
    for line in content_no_comments.split('\n'):
        # Only strip line comments if not inside a string - too complex for simple regex
        # Simplified: strip // if not inside quotes? 
        # Let's just do a basic brace count first on the raw content, hoping comments are balanced or ignored.
        pass

    # Better: Tokenize simply
    
    line_num = 1
    col_num = 0
    
    in_quote = None # ' or " or `
    escape = False
    in_line_comment = False
    in_block_comment = False
    
    for i, char in enumerate(content):
        # Track line/col
        if char == '\n':
            line_num += 1
            col_num = 0
            in_line_comment = False
            continue
        col_num += 1
        
        if in_line_comment:
            continue
            
        if in_block_comment:
            if char == '/' and i > 0 and content[i-1] == '*':
                in_block_comment = False
            continue
            
        # Check for start of comments
        if in_quote is None:
            if char == '/' and i + 1 < len(content):
                next_char = content[i+1]
                if next_char == '/':
                    in_line_comment = True
                    continue
                if next_char == '*':
                    in_block_comment = True
                    continue
        
        # Check quotes
        if char == '"' or char == "'" or char == '`':
            if in_quote is None:
                in_quote = char
            elif in_quote == char and not escape:
                in_quote = None
        
        if char == '\\' and in_quote:
            escape = not escape
        else:
            escape = False
            
        if in_quote:
            continue
            
        # Brackets
        if char in '({[':
            stack.append((char, line_num, col_num))
        elif char in ')}]':
            if not stack:
                print(f"Error: Unmatched {char} at line {line_num}:{col_num}")
                continue # don't return, keep checking
            
            last_char, last_line, last_col = stack.pop()
            # mapping maps Closing -> Opening.
            # We have Opening (last_char). We want to know if char (Closing) matches it.
            # So if mapping[char] == last_char
            
            if mapping[char] != last_char:
                print(f"Error: Mismatched {char} at line {line_num}:{col_num}. Expected closing for {last_char} from line {last_line}:{last_col}")
                continue

    if stack:
        print(f"FAILED: Stack not empty. {len(stack)} unclosed items.")
        for item in stack[:5]:
             print(f" - Unclosed {item[0]} from line {item[1]}:{item[2]}")
    else:
        print("SUCCESS: Brackets are balanced.")

check_syntax('/home/emmanuel/InterroPedago_4/teacher/frontend/index.html')
