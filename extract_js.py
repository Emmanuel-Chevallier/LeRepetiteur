import re
import os

html_path = 'teacher/frontend/index.html'
js_out_path = 'teacher/frontend/debug_script.js'

if not os.path.exists(html_path):
    print(f"File not found: {html_path}")
    exit(1)

with open(html_path, 'r') as f:
    content = f.read()

# Find the LAST script tag (the main logic one)
# We know it starts around line 665 and ends at the bottom
# But let's just grab everything between the last <script> and </script>
matches = list(re.finditer(r'<script>(.*?)</script>', content, re.DOTALL))
if not matches:
    print("No script tags found.")
    exit(1)

# Main script is likely the last one or the largest one
main_script = matches[-1].group(1)

with open(js_out_path, 'w') as f:
    f.write(main_script)

print(f"Extracted {len(main_script)} bytes to {js_out_path}")
