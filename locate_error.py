js_path = 'teacher/frontend/debug_script.js'
offset = 15585

with open(js_path, 'r') as f:
    content = f.read()

# Get substring around offset
start = max(0, offset - 100)
end = min(len(content), offset + 100)
print(f"Content around {offset}:")
print(content[start:end])

# Calculate line number
line_num = content[:offset].count('\n') + 1
print(f"Line number in JS: {line_num}")

# Now find this content in HTML to get real line number
html_path = 'teacher/frontend/index.html'
with open(html_path, 'r') as f:
    html_content = f.read()

snippet = content[offset-20:offset+20]
try:
    html_offset = html_content.index(snippet)
    html_line = html_content[:html_offset].count('\n') + 1
    print(f"Line number in HTML: {html_line}")
except ValueError:
    print("Snippet not unique or found in HTML")
