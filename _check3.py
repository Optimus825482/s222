import urllib.request, json

req = urllib.request.Request('http://localhost:8001/openapi.json')
req.add_header('User-Agent', 'test')
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
paths = sorted(data.get('paths', {}).keys())

# Find what routes exist around the cutoff point
# security/audit-log is the last one before identity section
print("All routes:")
for p in paths:
    print(f"  {p}")

# Now check what's in main.py around the security/audit-log route
with open("backend/main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the audit-log route and what comes after
for i, line in enumerate(lines):
    if "audit-log" in line and "@app" in line:
        print(f"\n--- audit-log route at line {i+1} ---")
        # Print 5 lines before and 30 after
        start = max(0, i-2)
        end = min(len(lines), i+30)
        for j in range(start, end):
            print(f"  {j+1}: {lines[j].rstrip()}")
        break
