import sys
import traceback

try:
    import uvicorn
    from backend.app.main import app
    print("Backend imported successfully. Starting uvicorn on 127.0.0.1:8000...", flush=True)
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, log_level="info", reload=False)
except Exception as e:
    print(f"Error starting backend: {e}", flush=True)
    traceback.print_exc()
