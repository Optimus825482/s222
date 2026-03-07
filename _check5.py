"""Test if main.py loads completely without errors."""
import sys
sys.path.insert(0, "backend")
sys.path.insert(0, ".")

# Capture stderr to see any warnings
import io
import contextlib

stderr_capture = io.StringIO()
with contextlib.redirect_stderr(stderr_capture):
    try:
        # This simulates what uvicorn does
        import importlib
        spec = importlib.util.spec_from_file_location("main", "backend/main.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        
        # Check routes
        routes = [r.path for r in mod.app.routes if hasattr(r, 'path') and '/api/' in r.path]
        bench = [r for r in routes if 'benchmark' in r]
        print(f"SUCCESS: {len(routes)} routes loaded")
        print(f"Benchmark routes: {len(bench)}")
    except Exception as e:
        print(f"FAILED at: {e}")
        import traceback
        traceback.print_exc()

stderr_output = stderr_capture.getvalue()
if stderr_output:
    print(f"\nSTDERR output:\n{stderr_output[:2000]}")
