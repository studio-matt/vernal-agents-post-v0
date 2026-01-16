# CORS Quick Reference

## 🚨 The Rule

**When `allow_credentials=True`, you CANNOT use `allow_origins=["*"]`**

Must use specific origins:
```python
allow_origins=[
    "https://machine.vernalcontentum.com",
    "https://themachine.vernalcontentum.com",
    "http://localhost:3000",
    "http://localhost:3001",
]
```

## 🔍 Quick Diagnostic

```bash
# 1. Is service running?
sudo systemctl status vernal-agents

# 2. Test CORS
curl -v -X OPTIONS http://127.0.0.1:8000/health \
  -H "Origin: https://machine.vernalcontentum.com" \
  2>&1 | grep -i "access-control"

# 3. Full diagnostic
bash scripts/diagnose_cors.sh
```

## 🛠️ Quick Fix

```bash
# 1. Check main.py
grep -A 10 "CORSMiddleware" main.py

# 2. If wrong, fix it (see CORS_EMERGENCY_NET.md)

# 3. Restart
sudo systemctl restart vernal-agents

# 4. Verify
curl -v -X OPTIONS http://127.0.0.1:8000/health \
  -H "Origin: https://machine.vernalcontentum.com" \
  2>&1 | grep -i "access-control"
```

## 📋 Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| No CORS headers | Service not running | `sudo systemctl restart vernal-agents` |
| Wildcard error | `allow_origins=["*"]` with credentials | Use specific origins |
| Wrong origin | Origin not in list | Add origin to `allow_origins` |
| Service won't start | Syntax/import error | `bash find_all_syntax_errors.sh` |

## 📚 Full Documentation

See `guardrails/CORS_EMERGENCY_NET.md` for complete guide.

