import pathlib
p = pathlib.Path('frontend/src/components/benchmark/run-tab.tsx')
content = p.read_text(encoding='utf-8')

# The clean component starts with "use client" and ends with the first standalone closing "}"
# after the return statement's closing </div>);
# Find the pattern: the component function's closing brace

# Strategy: find "export function RunTab()" and then count braces to find its end
start = content.find('export function RunTab()')
if start < 0:
    print("ERROR: Could not find RunTab")
    exit(1)

# Find the opening brace of the function
brace_start = content.find('{', start)
depth = 0
end = -1
i = brace_start
while i < len(content):
    ch = content[i]
    if ch == '{':
        depth += 1
    elif ch == '}':
        depth -= 1
        if depth == 0:
            end = i + 1
            break
    # Skip string literals
    elif ch in ('"', "'", '`'):
        quote = ch
        i += 1
        while i < len(content) and content[i] != quote:
            if content[i] == '\\':
                i += 1  # skip escaped char
            i += 1
    i += 1

if end < 0:
    print("ERROR: Could not find matching brace")
    exit(1)

# Get everything before the function (imports etc) + the function itself
header = content[:start]
func = content[start:end]
clean = header + func + '\n'

p.write_text(clean, encoding='utf-8')
lines = clean.count('\n') + 1
print(f'OK: cleaned to {lines} lines, {len(clean)} chars')
