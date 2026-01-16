# Master Diagnostic Router - Complete System Check

**Purpose:** One-stop comprehensive diagnostic guide that routes you through ALL testing, emergency nets, guardrails, and diagnostic procedures in the correct order.

**When to use:** 
- Something is broken and you don't know where to start
- After deployment to verify everything works
- Before deployment to catch issues early
- When you need a complete system health check
- When troubleshooting any backend issue

**Location:** `docs/MASTER_DIAGNOSTIC_ROUTER.md`

---

## 🎯 Quick Start: Run Full Diagnostic

```bash
cd /home/ubuntu/vernal-agents-post-v0
bash docs/run_full_diagnostic.sh
```

Or follow this document step-by-step.

---

## 📋 Master Diagnostic Checklist

Follow these steps in order. Each step will route you to the appropriate documentation or script.

### Phase 1: Service Health (CRITICAL - Start Here)

#### ✅ Step 1: Is the Service Running?

```bash
sudo systemctl status vernal-agents
```

**If NOT running:**
- **Route to:** `docs/EMERGENCY_NET_BACKEND.md` → "Service Won't Start" section
- **Also check:** `guardrails/SYNTAX_CHECKING.md` → Syntax errors prevent startup
- **Run:** `bash find_all_syntax_errors.sh`
- **Check logs:** `sudo journalctl -u vernal-agents --since "5 minutes ago" | tail -50`

**If running:**
- ✅ Continue to Step 2

---

#### ✅ Step 2: Is Port 8000 Listening?

```bash
sudo lsof -i :8000
```

**If NOT listening:**
- **Route to:** `docs/EMERGENCY_NET_BACKEND.md` → "Service Won't Start" section
- **Run:** `bash scripts/check_service_startup.sh`
- **Check logs:** Service may be crashing immediately after start

**If listening:**
- ✅ Continue to Step 3

---

#### ✅ Step 3: Can We Reach FastAPI Directly?

```bash
curl -v http://127.0.0.1:8000/health
```

**If connection refused:**
- Service not running (go back to Step 1)
- Wrong port or host binding

**If connection works:**
- ✅ Continue to Step 4

---

### Phase 2: CORS Configuration (Frontend Connectivity)

#### ✅ Step 4: CORS Diagnostic

```bash
bash scripts/diagnose_cors.sh
```

**If CORS errors found:**
- **Route to:** `guardrails/CORS_EMERGENCY_NET.md` → Complete fix guide
- **Quick fix:** `bash scripts/fix_cors_wildcard.sh` (if wildcard issue)
- **Quick reference:** `guardrails/CORS_QUICK_REFERENCE.md`

**Common issues:**
- Wildcard origins with credentials → Fix in `main.py`
- Service not running → Go back to Phase 1
- Nginx interference → Check nginx config

**If CORS OK:**
- ✅ Continue to Step 5

---

### Phase 3: Code Health (Syntax & Structure)

#### ✅ Step 5: Syntax Check

```bash
bash find_all_syntax_errors.sh
```

**If syntax errors found:**
- **Route to:** `guardrails/SYNTAX_CHECKING.md` → Complete syntax checking guide
- **Fix ALL errors** before continuing
- **Re-run:** `bash find_all_syntax_errors.sh` until clean

**If no errors:**
- ✅ Continue to Step 6

---

#### ✅ Step 6: Import Validation

```bash
cd /home/ubuntu/vernal-agents-post-v0
python3 -c "import main; print('✅ Imports OK')" 2>&1
```

**If import errors:**
- **Route to:** `guardrails/SYNTAX_CHECKING.md` → "Import Errors" section
- **Check:** Missing modules, wrong paths, circular imports
- **Fix:** Install missing packages or fix import paths

**If imports OK:**
- ✅ Continue to Step 7

---

#### ✅ Step 7: main.py Structure Validation

```bash
bash guardrails/validate_main_structure.sh
```

**If structure issues:**
- **Route to:** `guardrails/REFACTORING.md` → "main.py Structure" section
- **Check:** All routers included, CORS configured, no missing imports

**If structure OK:**
- ✅ Continue to Step 8

---

### Phase 4: Router & Endpoint Health

#### ✅ Step 8: Router Inclusion Check

```bash
cd /home/ubuntu/vernal-agents-post-v0
grep -E "app.include_router|from app.routes" main.py
```

**Expected routers:**
- `admin_router`
- `auth_router`
- `platforms_router`
- `content_router`
- `campaigns_research_router`
- `brand_personalities_router`

**If routers missing:**
- **Route to:** `guardrails/REFACTORING.md` → "Router Extraction" section
- **Fix:** Add missing router includes

**If all routers present:**
- ✅ Continue to Step 9

---

#### ✅ Step 9: Endpoint Health Check

```bash
# Health endpoint
curl -s http://127.0.0.1:8000/health | jq .

# Root endpoint
curl -s http://127.0.0.1:8000/ | jq .

# Admin endpoint (may require auth)
curl -s -X OPTIONS http://127.0.0.1:8000/admin/settings/research_agents_list \
  -H "Origin: https://machine.vernalcontentum.com" \
  2>&1 | grep -i "access-control"
```

**If endpoints fail:**
- **Route to:** `REFACTORING_TESTING_CHECKLIST.md` → "Endpoint Testing" section
- **Check:** Router imports, route definitions, middleware order

**If endpoints OK:**
- ✅ Continue to Step 10

---

### Phase 5: Database & Configuration

#### ✅ Step 10: Database Connectivity

```bash
# Check if database health endpoint exists
curl -s http://127.0.0.1:8000/mcp/enhanced/health 2>&1 | head -5
```

**If database errors:**
- **Route to:** `docs/EMERGENCY_NET_BACKEND.md` → "Database Issues" section
- **Check:** `.env` file exists with correct credentials
- **Verify:** Database server is accessible

**If database OK:**
- ✅ Continue to Step 11

---

#### ✅ Step 11: Environment Configuration

```bash
cd /home/ubuntu/vernal-agents-post-v0
if [ -f ".env" ]; then
    echo "✅ .env file exists"
    # Check for real credentials (not placeholders)
    if grep -qE "DB_HOST.*50\.6\.198\.220|DB_USER.*vernalcontentum" .env 2>/dev/null; then
        echo "✅ .env contains production credentials"
    else
        echo "⚠️  Warning: .env may contain placeholder credentials"
    fi
else
    echo "❌ .env file NOT found (CRITICAL)"
    echo "Route to: docs/EMERGENCY_NET_BACKEND.md → Environment Setup"
fi
```

**If .env issues:**
- **Route to:** `docs/EMERGENCY_NET_BACKEND.md` → "Environment Variables" section
- **Fix:** Restore from backup or recreate `.env` file

**If .env OK:**
- ✅ Continue to Step 12

---

### Phase 6: Nginx & External Access

#### ✅ Step 12: Nginx Configuration

```bash
sudo nginx -t
```

**If nginx errors:**
- **Route to:** `docs/EMERGENCY_NET_BACKEND.md` → "Nginx Configuration" section
- **Fix:** Correct nginx config errors
- **Reload:** `sudo nginx -s reload`

**If nginx OK:**
- ✅ Continue to Step 13

---

#### ✅ Step 13: External Access Test

```bash
curl -v https://themachine.vernalcontentum.com/health \
  -H "Origin: https://machine.vernalcontentum.com" \
  2>&1 | grep -i "access-control"
```

**If external access fails:**
- **Route to:** `docs/EMERGENCY_NET_BACKEND.md` → "External Access" section
- **Check:** Nginx proxy configuration, SSL certificates, firewall rules

**If external access OK:**
- ✅ Continue to Step 14

---

### Phase 7: Recent Errors & Logs

#### ✅ Step 14: Recent Error Check

```bash
ERROR_COUNT=$(sudo journalctl -u vernal-agents --since "10 minutes ago" 2>/dev/null | grep -iE "error|❌|CRITICAL|Exception|Traceback" | wc -l)
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "⚠️  Found $ERROR_COUNT errors in last 10 minutes:"
    sudo journalctl -u vernal-agents --since "10 minutes ago" | grep -iE "error|❌|CRITICAL|Exception|Traceback" | tail -20
else
    echo "✅ No recent errors in logs"
fi
```

**If errors found:**
- **Route to:** `docs/EMERGENCY_NET_BACKEND.md` → "Troubleshooting" section
- **Check:** Error patterns, stack traces, related documentation
- **Fix:** Address root cause

**If no errors:**
- ✅ Continue to Step 15

---

### Phase 8: Feature-Specific Checks

#### ✅ Step 15: Feature Testing (If Applicable)

**If testing specific features:**
- **Route to:** `TESTING_CHECKLIST.md` → Feature-specific test steps
- **Route to:** `REFACTORING_TESTING_CHECKLIST.md` → Infrastructure testing
- **Route to:** `docs/HOW_TO_TEST_CREWAI.md` → CrewAI testing

**Common feature checks:**
- Author personality analysis
- Content generation
- Platform posting
- Research agents
- Campaign management

---

## 🗺️ Decision Tree: What's Broken?

### **Service Won't Start**
1. ✅ Step 1: Check service status
2. ✅ Step 5: Run syntax check
3. ✅ Step 6: Check imports
4. **Route to:** `docs/EMERGENCY_NET_BACKEND.md` → "Service Won't Start"
5. **Route to:** `guardrails/SYNTAX_CHECKING.md` → Fix syntax errors

### **CORS Errors**
1. ✅ Step 4: Run CORS diagnostic
2. **Route to:** `guardrails/CORS_EMERGENCY_NET.md` → Complete fix guide
3. **Quick fix:** `bash scripts/fix_cors_wildcard.sh`

### **Frontend Can't Connect**
1. ✅ Step 1: Service running?
2. ✅ Step 2: Port 8000 listening?
3. ✅ Step 3: Health endpoint works?
4. ✅ Step 4: CORS configured?
5. ✅ Step 13: External access works?

### **Import Errors**
1. ✅ Step 6: Import validation
2. **Route to:** `guardrails/SYNTAX_CHECKING.md` → "Import Errors" section
3. Fix missing modules or import paths

### **After Refactoring**
1. **CRITICAL:** Compare with backup: `bash guardrails/compare_refactor.sh`
   - Shows what changed (added/removed/modified)
   - Fastest way to diff old monolith vs new refactor
   - Track code snippets to find why things broke
2. ✅ Step 5: Syntax check
3. ✅ Step 6: Import validation
4. ✅ Step 7: Structure validation
5. ✅ Step 8: Router inclusion check
6. ✅ Step 9: Endpoint health check
7. **Route to:** `guardrails/REFACTORING.md` → Complete refactoring guide
8. **Route to:** `REFACTORING_TESTING_CHECKLIST.md` → Testing procedures
9. **If issues found:** `bash guardrails/restore_from_backup.sh [timestamp]` to restore

### **After Deployment**
1. ✅ All Phase 1 steps (Service Health)
2. ✅ All Phase 2 steps (CORS)
3. ✅ All Phase 3 steps (Code Health)
4. ✅ All Phase 4 steps (Routers)
5. ✅ Step 13: External access
6. ✅ Step 14: Recent errors

### **Before Deployment**
1. **If refactoring:** Create backup: `bash guardrails/backup_before_refactor.sh`
2. ✅ Step 5: Syntax check
3. ✅ Step 6: Import validation
4. ✅ Step 7: Structure validation
5. ✅ Step 8: Router inclusion
6. **Route to:** `guardrails/REFACTORING.md` → Pre-deployment checklist

---

## 📚 Document Reference Map

### Emergency & Critical
- **`docs/EMERGENCY_NET_BACKEND.md`** - Server setup, deployment, critical issues
- **`docs/EMERGENCY_NET.md`** - Frontend emergency procedures
- **`guardrails/CORS_EMERGENCY_NET.md`** - CORS fix guide (specific origins with credentials)

### Guardrails & Prevention
- **`guardrails/REFACTORING.md`** - Refactoring best practices, main.py structure
- **`guardrails/SYNTAX_CHECKING.md`** - Syntax error detection and fixing
- **`guardrails/CORS_QUICK_REFERENCE.md`** - CORS quick reference
- **`guardrails/QUICK_REFERENCE.md`** - General quick reference

### Testing & Validation
- **`TESTING_CHECKLIST.md`** - Feature testing checklist
- **`REFACTORING_TESTING_CHECKLIST.md`** - Infrastructure/refactoring testing
- **`docs/HOW_TO_TEST_CREWAI.md`** - CrewAI agent testing

### Diagnostic Scripts
- **`scripts/diagnose_cors.sh`** - Comprehensive CORS diagnostic
- **`scripts/fix_cors_wildcard.sh`** - Auto-fix wildcard CORS issue
- **`scripts/check_service_startup.sh`** - Service startup diagnostics
- **`find_all_syntax_errors.sh`** - Comprehensive syntax checker
- **`guardrails/validate_main_structure.sh`** - main.py structure validation

### Feature Documentation
- **`docs/GUARDRAILS_SYSTEM.md`** - Guardrails UI system
- **`docs/SYSTEM_MODEL_SETTINGS.md`** - System model settings
- **`docs/DEBUG_RESEARCH_AGENTS.md`** - Research agent debugging

---

## 🔄 Complete Diagnostic Workflow

### Quick Diagnostic (5 minutes)
```bash
# Run automated checks
bash scripts/diagnose_cors.sh
bash find_all_syntax_errors.sh
bash guardrails/validate_main_structure.sh
```

### Full Diagnostic (15-30 minutes)
Follow all 15 steps in this document in order.

### Pre-Deployment Diagnostic (10 minutes)
1. Steps 5-8 (Code Health & Structure)
2. Step 4 (CORS)
3. Step 9 (Endpoints)

### Post-Deployment Diagnostic (10 minutes)
1. Steps 1-3 (Service Health)
2. Step 4 (CORS)
3. Step 13 (External Access)
4. Step 14 (Recent Errors)

---

## 🎯 Success Criteria

All diagnostics pass when:
- ✅ Service is running and healthy
- ✅ Port 8000 is listening
- ✅ Health endpoint responds
- ✅ CORS headers are correct (specific origins, not wildcard)
- ✅ No syntax errors
- ✅ All imports work
- ✅ main.py structure is valid
- ✅ All routers are included
- ✅ Endpoints respond correctly
- ✅ Database connectivity works
- ✅ .env file exists with correct credentials
- ✅ Nginx configuration is valid
- ✅ External access works
- ✅ No recent errors in logs

---

## 📝 Notes

- **Always start with Phase 1** (Service Health) - most issues are service not running
- **Run syntax checks before deployment** - prevents 90% of startup failures
- **CORS issues are usually configuration** - check `main.py` for wildcard origins
- **Use decision tree** if you know what's broken
- **Follow document routes** for detailed procedures
- **Run full diagnostic after major changes**

---

## 🔗 Quick Links

- [Emergency Net Backend](./EMERGENCY_NET_BACKEND.md) - Critical issues
- [CORS Emergency Net](../guardrails/CORS_EMERGENCY_NET.md) - CORS fixes
- [Syntax Checking](../guardrails/SYNTAX_CHECKING.md) - Syntax errors
- [Refactoring Guide](../guardrails/REFACTORING.md) - Code structure
- [Testing Checklist](../TESTING_CHECKLIST.md) - Feature testing
- [Documentation Index](./DOCUMENTATION_INDEX.md) - All docs

---

**Last Updated:** 2025-01-XX  
**Maintained by:** Development Team  
**Purpose:** Master diagnostic router for comprehensive system health checks

