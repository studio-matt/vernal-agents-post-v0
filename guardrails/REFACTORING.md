# Refactoring Guardrails

**Purpose:** Prevent common refactoring mistakes that break the application.

---

## 🚨 Critical Rule: Never Delete `main.py`

### What Happened
During route extraction refactoring, `main.py` was gradually emptied but never properly cleaned up. The file still contained:
- ✅ Router includes (correct)
- ❌ Duplicate endpoint definitions (should have been removed)

This caused the service to fail because `main.py` was missing the minimal entry point structure.

### The Correct Structure

After extracting routes to `app/routes/*.py`, `main.py` should be a **thin entry point** (50-150 lines) that:

1. **Creates FastAPI app**
   ```python
   app = FastAPI(title="Vernal Agents API", version="1.0.0")
   ```

2. **Configures CORS middleware**
   ```python
   app.add_middleware(CORSMiddleware, ...)
   ```

3. **Includes all routers**
   ```python
   from app.routes.admin import admin_router
   app.include_router(admin_router)
   # ... repeat for all routers
   ```

4. **Basic health endpoints** (optional)
   ```python
   @app.get("/health")
   async def health_check():
       return {"status": "ok"}
   ```

5. **Entry point** (if running directly)
   ```python
   if __name__ == "__main__":
       import uvicorn
       uvicorn.run(app, host="0.0.0.0", port=8000)
   ```

### What NOT to Include in `main.py`

❌ **Don't include:**
- Endpoint definitions (use routers instead)
- Business logic
- Database models
- Helper functions (move to `app/utils/`)
- Complex imports that aren't needed for app initialization

---

## Refactoring Checklist

When extracting routes from `main.py`:

### Before Starting
- [ ] **Create backup:** `bash guardrails/backup_before_refactor.sh`
  - This saves `main.py` and all route files to `.refactor_backups/`
  - Backup includes timestamp for easy comparison later
  - **CRITICAL:** Always backup before refactoring - enables fast diff/debugging
- [ ] Run syntax check: `bash find_all_syntax_errors.sh`
- [ ] Verify service is running: `curl http://127.0.0.1:8000/health`

### During Extraction
- [ ] Create router file: `app/routes/{feature}_router.py`
- [ ] Move endpoint functions to router
- [ ] Create `{feature}_router = APIRouter()` in router file
- [ ] Add `@{feature}_router.get/post/put/delete` decorators
- [ ] Import router in `main.py`: `from app.routes.{feature} import {feature}_router`
- [ ] Include router: `app.include_router({feature}_router)`
- [ ] **Remove duplicate endpoint definitions from `main.py`** ⚠️

### After Extraction
- [ ] **Compare with backup:** `bash guardrails/compare_refactor.sh`
  - Shows what changed (added/removed/modified)
  - Helps identify lost functionality
  - Fast way to diff old monolith vs new refactor
- [ ] Run syntax check: `bash find_all_syntax_errors.sh`
- [ ] Verify `main.py` is < 200 lines
- [ ] Verify `main.py` only has:
  - FastAPI app creation
  - CORS middleware
  - Router includes
  - Health endpoints (if any)
- [ ] Test service starts: `python3 -c "import main; print('✅ Import successful')"`
- [ ] Restart service: `sudo systemctl restart vernal-agents`
- [ ] Verify health endpoint: `curl http://127.0.0.1:8000/health`
- [ ] Test at least one endpoint from the extracted router
- [ ] **If issues found:** `bash guardrails/restore_from_backup.sh [timestamp]` to restore

### Validation Script

Run this after refactoring:
```bash
bash guardrails/validate_main_structure.sh
```

---

## Common Refactoring Mistakes

### 1. Forgetting to Remove Duplicate Endpoints
**Symptom:** Endpoints work but code is duplicated in `main.py` and router file.

**Fix:** After extracting to router, delete the endpoint definition from `main.py`.

### 2. Not Including Router in `main.py`
**Symptom:** Service starts but endpoints return 404.

**Fix:** Add `app.include_router({feature}_router)` to `main.py`.

### 3. Breaking Import Paths
**Symptom:** `ImportError` or `ModuleNotFoundError` when starting service.

**Fix:** 
- Use relative imports: `from app.routes.admin import admin_router`
- Or absolute imports: `from app.routes.admin import admin_router`
- Check `app/routes/__init__.py` exists

### 4. Missing Dependencies in Router
**Symptom:** `NameError` for functions like `get_db()`, `get_current_user()`.

**Fix:** 
- Import dependencies in router file
- Or import from `main.py` if shared (not recommended - move to `app/utils/`)

### 5. CORS Not Configured
**Symptom:** Frontend gets CORS errors after refactoring.

**Fix:** Ensure CORS middleware is in `main.py` (not in router files).

---

## Router Extraction Template

```python
# app/routes/{feature}.py
"""
{Feature} endpoints extracted from main.py
Moved from main.py to preserve API contract parity
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from auth_api import get_current_user
from database import SessionLocal

logger = logging.getLogger(__name__)

{feature}_router = APIRouter()

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@{feature}_router.get("/{feature}")
async def get_{feature}(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get {feature} - requires authentication"""
    # ... implementation
    pass
```

Then in `main.py`:
```python
try:
    from app.routes.{feature} import {feature}_router
    app.include_router({feature}_router)
    logger.info("✅ {Feature} router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include {feature} router: {e}")
```

---

## Verification Commands

After any refactoring, run these:

```bash
# 1. Syntax check
bash find_all_syntax_errors.sh

# 2. Verify main.py structure
python3 -c "
import ast
with open('main.py') as f:
    tree = ast.parse(f.read())
    endpoints = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and any(d.id == 'app' for d in n.decorator_list if isinstance(d, ast.Attribute))]
    print(f'Found {len(endpoints)} endpoint definitions in main.py')
    if len(endpoints) > 2:
        print('⚠️  WARNING: main.py should only have health/root endpoints')
    else:
        print('✅ main.py structure looks good')
"

# 3. Test import
python3 -c "import main; print('✅ Import successful')"

# 4. Check service
curl http://127.0.0.1:8000/health
```

---

## Backup & Comparison Tools

### Creating Backups

**Before any refactoring:**
```bash
# Backup main.py and all route files
bash guardrails/backup_before_refactor.sh

# Or backup specific files
bash guardrails/backup_before_refactor.sh main.py app/routes/admin.py
```

Backups are saved to `.refactor_backups/[timestamp]/` with full directory structure preserved.

### Comparing Refactored Code

**After refactoring, compare with original:**
```bash
# Compare with most recent backup
bash guardrails/compare_refactor.sh

# Or specify backup timestamp
bash guardrails/compare_refactor.sh 20250115_143022
```

This shows:
- ✅ Unchanged files
- 🔀 Modified files (with line counts)
- ❌ Missing files (deleted during refactor)
- ✨ New files (added during refactor)

**To see detailed diffs:**
```bash
# View diff for specific file
diff -u .refactor_backups/[timestamp]/main.py main.py

# Side-by-side comparison
diff -y .refactor_backups/[timestamp]/main.py main.py | less

# Find what broke - compare function definitions
grep -E '^(def |async def )' .refactor_backups/[timestamp]/main.py main.py
```

### Restoring from Backup

**If refactoring broke something:**
```bash
# Restore all files from backup
bash guardrails/restore_from_backup.sh [timestamp]

# Or restore specific files
bash guardrails/restore_from_backup.sh [timestamp] main.py app/routes/admin.py
```

**Why backups matter:**
- Fastest way to diff old monolith vs new refactor
- Track code snippets to find why things broke
- Compare function definitions, imports, router includes
- Restore quickly if refactoring goes wrong

---

## Related Documentation

- [Syntax Checking](./SYNTAX_CHECKING.md) - Validate Python syntax
- [Quick Reference](./QUICK_REFERENCE.md) - Essential commands
- [Code Health Workflow](../../docs-system/workflows/code_health.md) - Refactor prompt generator

---

## Lessons Learned

1. **Always keep `main.py` as a thin entry point** - Never delete it entirely
2. **Remove duplicate code** - After extracting to router, delete from `main.py`
3. **Test after each extraction** - Don't extract multiple features at once
4. **Use validation scripts** - Automate checks to catch mistakes early
5. **Document the refactor** - Note what was moved and where

---

**Last Updated:** 2025-01-XX  
**Related Issue:** main.py was deleted during refactoring, causing service failure

