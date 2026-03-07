with open("backend/main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find all @app route decorators and their line numbers
routes = []
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("@app.") and ("get(" in stripped or "post(" in stripped or "put(" in stripped or "delete(" in stripped or "websocket(" in stripped):
        routes.append((i+1, stripped))

print(f"Total route decorators: {len(routes)}")
print("\n--- Routes from line 3300+ (identity and beyond) ---")
for ln, route in routes:
    if ln >= 3300:
        print(f"  Line {ln}: {route}")

print("\n--- Last 10 routes before line 3300 ---")
before = [(ln, r) for ln, r in routes if ln < 3300]
for ln, route in before[-10:]:
    print(f"  Line {ln}: {route}")

# Also find where teachability, skills, system/overview are
print("\n--- Key routes ---")
for ln, route in routes:
    if any(k in route for k in ['teachability', 'skills', 'system/overview', 'identity']):
        print(f"  Line {ln}: {route}")
