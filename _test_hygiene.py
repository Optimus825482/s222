"""Quick test script for hygiene endpoint"""
import urllib.request
import json

# Check openapi for hygiene routes
r = urllib.request.urlopen("http://localhost:8001/openapi.json")
data = json.loads(r.read())
hygiene_paths = [p for p in data.get("paths", {}) if "hygiene" in p]
print(f"Hygiene routes in OpenAPI: {hygiene_paths}")

# Try calling hygiene endpoint
try:
    req = urllib.request.Request(
        "http://localhost:8001/api/skills/hygiene?dry_run=true",
        method="POST",
        data=b"",
    )
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    print(f"Hygiene result: {json.dumps(result, indent=2)}")
except Exception as e:
    print(f"Hygiene call failed: {e}")

# Try direct import test
try:
    import sys, os
    sys.path.insert(0, os.getcwd())
    from tools.skill_hygiene import run_hygiene_check
    result = run_hygiene_check(dry_run=True)
    print(f"\nDirect call result: {json.dumps(result, indent=2, default=str)}")
except Exception as e:
    print(f"Direct import failed: {e}")
