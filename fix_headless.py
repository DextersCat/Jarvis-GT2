#!/usr/bin/env python
"""Fix jarvis_main.py for headless mode (remove Tkinter console references)"""

with open('jarvis_main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and fix the log method
output = []
i = 0
while i < len(lines):
    # Look for the problematic log() method
    if '"""Log to both GUI console' in lines[i]:
        # Skip the old docstring
        output.append('        """Log to system logger and dashboard (headless mode)."""\n')
        i += 1
        # Skip lines until we hit the logger.info call
        while i < len(lines) and 'logger.info(text)' not in lines[i]:
            if 'if hasattr(self, \'console\')' in lines[i]:
                # Skip the console block entirely
                indent_level = len(lines[i]) - len(lines[i].lstrip())
                i += 1
                # Skip until we find a line with same or lower indent
                while i < len(lines):
                    current_indent = len(lines[i]) - len(lines[i].lstrip())
                    if lines[i].strip() and current_indent <= indent_level:
                        break
                    i += 1
            else:
                i += 1
        if i < len(lines) and 'logger.info(text)' in lines[i]:
            output.append(lines[i])
            i += 1
    else:
        output.append(lines[i])
        i += 1

with open('jarvis_main.py', 'w', encoding='utf-8') as f:
    f.writelines(output)

print("✅ Fixed log() method - removed Tkinter console references")
