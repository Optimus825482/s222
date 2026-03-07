import urllib.request, json

req = urllib.request.Request('http://localhost:8001/openapi.json')
req.add_header('User-Agent', 'test')
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
paths = sorted(data.get('paths', {}).keys())

# Find the last few routes alphabetically
print("Last 10 routes in running backend:")
for p in paths[-10:]:
    print(f"  {p}")

# Check if identity routes exist (they're right before benchmarks)
identity = [p for p in paths if 'identity' in p]
print(f"\nIdentity routes: {identity}")

# Check audit-log
audit = [p for p in paths if 'audit' in p]
print(f"Audit routes: {audit}")
