# RazControl Dashboard

Serve this directory on port 5173 after starting the backend on port 8000:

```powershell
python -m http.server 5173 -d frontend
```

The dashboard uses the real API at `http://localhost:8000` by default. Change the backend URL in the sidebar if needed.
