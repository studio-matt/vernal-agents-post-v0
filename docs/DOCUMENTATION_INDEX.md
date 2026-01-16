# Documentation Index - When to Use What

**Purpose:** Quick reference guide to all documentation, explaining what each document is for and when to use it.

**Last Updated:** 2025-01-XX

---

## 🎯 Master Diagnostic Router (START HERE)

### **MASTER_DIAGNOSTIC_ROUTER.md**
**When to use:**
- Something is broken and you don't know where to start
- Need a complete system health check
- After deployment to verify everything works
- Before deployment to catch issues early
- When troubleshooting any backend issue

**What it contains:**
- **15-step comprehensive diagnostic checklist** (all phases)
- Decision tree for common issues
- Routes to all other documentation
- Complete workflow procedures
- Success criteria

**Location:** `docs/MASTER_DIAGNOSTIC_ROUTER.md`

**Quick access:**
```bash
# Run full automated diagnostic:
bash docs/run_full_diagnostic.sh

# Or follow step-by-step:
cat docs/MASTER_DIAGNOSTIC_ROUTER.md
```

**This is your ONE-STOP diagnostic guide** - it routes you to all other docs.

---

## 🚨 Emergency / Critical Issues

### **EMERGENCY_NET_BACKEND.md**
**When to use:** 
- Service won't start
- Deployment is broken
- Need to understand server setup quickly
- Critical production issues

**What it contains:**
- Server details (IP, paths, deployment flow)
- Code preservation rules (CRITICAL - prevents regressions)
- Deployment procedures
- Troubleshooting common issues
- Emergency reset procedures

**Location:** `docs/EMERGENCY_NET_BACKEND.md`

**Quick access:**
```bash
# On server, when things are broken:
cd /home/ubuntu/vernal-agents-post-v0
# Then follow EMERGENCY_NET_BACKEND.md procedures
```

---

## 🛡️ Guardrails (Prevention & Safety)

### **guardrails/REFACTORING.md**
**When to use:**
- Before extracting routes from `main.py`
- Before refactoring code structure
- When `main.py` structure needs validation
- After refactoring to verify correctness

**What it contains:**
- Critical rule: Never delete `main.py`
- Refactoring checklist (before/during/after)
- Common mistakes and fixes
- Router extraction template
- Verification commands

**Location:** `guardrails/REFACTORING.md`

**Quick access:**
```bash
# Before refactoring:
cat guardrails/REFACTORING.md

# After refactoring:
bash guardrails/validate_main_structure.sh
```

---

### **guardrails/SYNTAX_CHECKING.md**
**When to use:**
- After making code changes
- Before deployment
- When service won't start (syntax errors)
- After refactoring
- When imports are broken

**What it contains:**
- `find_all_syntax_errors.sh` - Comprehensive syntax checker
- `scripts/check_syntax_patterns.py` - Pattern-based error detection
- Usage instructions
- Common errors and fixes

**Location:** `guardrails/SYNTAX_CHECKING.md`

**Quick access:**
```bash
# Always run before deployment:
bash find_all_syntax_errors.sh
```
---

### **guardrails/CORS_EMERGENCY_NET.md**
**When to use:**
- Frontend shows CORS errors
- Browser console: "No 'Access-Control-Allow-Origin' header"
- Browser console: "wildcard '*' when credentials mode is 'include'"
- Preflight requests failing
- Service running but frontend can't connect

**What it contains:**
- **The exact fix that works** - Specific origins with credentials
- Complete diagnostic checklist (14 steps)
- Common issues and solutions
- Step-by-step fix procedures
- Quick reference commands

**Location:** `guardrails/CORS_EMERGENCY_NET.md`

**Quick access:**
```bash
# Diagnose CORS issues:
bash scripts/diagnose_cors.sh

# Quick reference:
cat guardrails/CORS_QUICK_REFERENCE.md

# Auto-fix wildcard issue:
bash scripts/fix_cors_wildcard.sh
```

**Key Rule:** When `allow_credentials=True`, you CANNOT use `allow_origins=["*"]` - must use specific origins.

---

### **guardrails/CORS_QUICK_REFERENCE.md**
**When to use:**
- Quick CORS fix needed
- Don't remember the exact rule
- Need one-page cheat sheet

**What it contains:**
- The critical rule (wildcard vs specific origins)
- Quick diagnostic commands
- Common issues table
- Quick fix procedure

**Location:** `guardrails/CORS_QUICK_REFERENCE.md`

**Quick access:**
```bash
cat guardrails/CORS_QUICK_REFERENCE.md
```

---

### **guardrails/README.md**
**When to use:**
- Overview of guardrails system
- Understanding what guardrails exist
- Finding specific guardrail documentation

**What it contains:**
- Links to all guardrail documentation
- Principles of the guardrails system
- Quick navigation

**Location:** `guardrails/README.md`

---

## 🧪 Testing & Validation

### **REFACTORING_TESTING_CHECKLIST.md**
**When to use:**
- After refactoring `main.py`
- After adding/removing routers
- When service won't start after changes
- When debugging CORS issues
- After infrastructure changes

**What it contains:**
- Step-by-step testing procedures
- Service health checks
- CORS validation
- Router endpoint testing
- Troubleshooting guide

**Location:** `REFACTORING_TESTING_CHECKLIST.md`

**Quick access:**
```bash
# After refactoring:
bash verify_service.sh
# Then follow REFACTORING_TESTING_CHECKLIST.md
```

---

### **verify_service.sh**
**When to use:**
- After restarting service
- Quick health check
- Verifying deployment worked

**What it contains:**
- Service status check
- Health endpoint test
- CORS headers check
- Recent logs review
- `main.py` structure validation

**Location:** `verify_service.sh`

**Quick access:**
```bash
bash verify_service.sh
```

---

## 📚 Feature Documentation

### **docs/GUARDRAILS_SYSTEM.md**
**When to use:**
- Understanding the guardrails UI in admin panel
- Code health scanning features
- Refactor prompt generator usage
- Gas meter widget

**What it contains:**
- Frontend guardrails system overview
- Code health scanner documentation
- API endpoints for code health
- Environment variables

**Location:** `docs/GUARDRAILS_SYSTEM.md`

---

## 🔍 Diagnostic Guides

### **docs/CORS_DIAGNOSTIC_GUIDE.md**
**When to use:**
- CORS errors in browser console
- Frontend can't call backend API
- Preflight requests failing

**What it contains:**
- Step-by-step CORS diagnosis
- Backend CORS configuration checks
- Nginx configuration verification
- Testing procedures

**Location:** `docs/CORS_DIAGNOSTIC_GUIDE.md`

**Quick access:**
```bash
# When CORS errors occur:
# Follow docs/CORS_DIAGNOSTIC_GUIDE.md
```

---

## 📋 Quick Reference

### **guardrails/QUICK_REFERENCE.md**
**When to use:**
- Need quick command reference
- Don't remember exact syntax
- Fast lookup for common tasks

**What it contains:**
- Essential commands for syntax checking
- Quick validation commands
- Common troubleshooting commands

**Location:** `guardrails/QUICK_REFERENCE.md`

---

## 🗺️ Decision Tree: Which Document Do I Need?

### **Service Won't Start**
1. Check `EMERGENCY_NET_BACKEND.md` - Server setup, deployment flow
2. Run `bash find_all_syntax_errors.sh` - Syntax errors
3. Check `guardrails/REFACTORING.md` - If you just refactored

### **CORS Errors**
1. **START HERE:** `guardrails/CORS_EMERGENCY_NET.md` - Complete fix guide with exact solution
2. Run `bash scripts/diagnose_cors.sh` - Comprehensive diagnostic
3. If wildcard issue: `bash scripts/fix_cors_wildcard.sh` - Auto-fix
4. Quick reference: `guardrails/CORS_QUICK_REFERENCE.md` - One-page cheat sheet
5. Legacy: `docs/CORS_DIAGNOSTIC_GUIDE.md` - Alternative diagnostic approach

### **After Refactoring**
1. Read `guardrails/REFACTORING.md` - Best practices
2. Run `bash guardrails/validate_main_structure.sh` - Structure validation
3. Run `bash find_all_syntax_errors.sh` - Syntax check
4. Follow `REFACTORING_TESTING_CHECKLIST.md` - Testing procedures

### **Before Deployment**
1. Run `bash find_all_syntax_errors.sh` - Syntax validation
2. Run `bash guardrails/validate_main_structure.sh` - Structure check
3. Check `EMERGENCY_NET_BACKEND.md` - Deployment procedures
4. Run `bash verify_service.sh` - After restart

### **Code Health Issues**
1. Check `docs/GUARDRAILS_SYSTEM.md` - Understanding the system
2. Use admin panel → System → Guard Rails
3. Check `docs-system/workflows/code_health.md` - Workflow details

### **Import Errors**
1. Run `bash find_all_syntax_errors.sh` - Find all import issues
2. Check `guardrails/SYNTAX_CHECKING.md` - Import validation
3. Check `EMERGENCY_NET_BACKEND.md` - Code preservation rules

---

## 📖 Document Relationships

```
EMERGENCY_NET_BACKEND.md (Critical Issues)
    ├── Deployment procedures
    ├── Server setup
    └── Code preservation rules

guardrails/
    ├── REFACTORING.md (Before/After Refactoring)
    │   └── References: SYNTAX_CHECKING.md
    ├── SYNTAX_CHECKING.md (Syntax Validation)
    │   └── Used by: REFACTORING.md, EMERGENCY_NET_BACKEND.md
    └── QUICK_REFERENCE.md (Quick Commands)
        └── References: SYNTAX_CHECKING.md

REFACTORING_TESTING_CHECKLIST.md (Testing)
    └── References: guardrails/REFACTORING.md

verify_service.sh (Quick Health Check)
    └── Used by: REFACTORING_TESTING_CHECKLIST.md

guardrails/
    ├── CORS_EMERGENCY_NET.md (CORS Fix - PRIMARY)
    ├── CORS_QUICK_REFERENCE.md (CORS Quick Ref)
    └── ... (other guardrails)

docs/
    ├── CORS_DIAGNOSTIC_GUIDE.md (CORS Issues - Legacy)
    └── GUARDRAILS_SYSTEM.md (Feature Docs)
```

---

## 🎯 Common Workflows

### **New Feature Development**
1. Develop feature
2. Run `bash find_all_syntax_errors.sh`
3. Test locally
4. Deploy following `EMERGENCY_NET_BACKEND.md`

### **Refactoring Workflow**
1. Read `guardrails/REFACTORING.md`
2. Create backup
3. Extract routes/modules
4. Run `bash guardrails/validate_main_structure.sh`
5. Run `bash find_all_syntax_errors.sh`
6. Follow `REFACTORING_TESTING_CHECKLIST.md`

### **Emergency Fix Workflow**
1. Check `EMERGENCY_NET_BACKEND.md` for server details
2. Run `bash find_all_syntax_errors.sh` for syntax issues
3. Run `bash verify_service.sh` for health check
4. Check relevant diagnostic guide (CORS, etc.)

---

## 📝 Notes

- **Always run syntax checks before deployment**
- **Read refactoring guide before extracting code**
- **Use emergency net for critical production issues**
- **Guardrails prevent problems - use them proactively**
- **Testing checklists ensure nothing breaks**

---

## 🔄 Keeping This Updated

When adding new documentation:
1. Add entry to this index
2. Update decision tree if needed
3. Update document relationships
4. Add to relevant workflow section

---

**Quick Links:**
- [Emergency Net](./EMERGENCY_NET_BACKEND.md) - Critical issues
- [Refactoring Guide](../guardrails/REFACTORING.md) - Before refactoring
- [Syntax Checking](../guardrails/SYNTAX_CHECKING.md) - Before deployment
- [Testing Checklist](../REFACTORING_TESTING_CHECKLIST.md) - After changes

