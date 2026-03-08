import pathlib
p = pathlib.Path("frontend") / "src" / "components" / "benchmark" / "run-tab.tsx"
lines = p.read_text(encoding="utf-8").splitlines()
print(f"Total lines: {len(lines)}")
for i in [0, 199, 209, len(lines)-1]:
    if 0 <= i < len(lines):
        print(f"  Line {i+1}: {lines[i][:80]}")
