# Maintenance + Diagnostics - Admin Panel Guide

**Purpose:** Clear instructions for admin users on how to use the Master Diagnostic Router and diagnostic system from the admin panel.

**Location:** Admin Panel → System → Maintenance + Diagnostics

---

## 🎯 Overview

The Maintenance + Diagnostics section provides a comprehensive diagnostic system to help you quickly identify and resolve system issues. It includes:

- **15-step diagnostic checklist** across 7 phases
- **Automated diagnostic script** that runs all checks
- **Decision trees** for common issues
- **Direct links** to all relevant documentation

---

## 📋 How to Use

### Option 1: Run Automated Full Diagnostic (Recommended)

1. **Click "Run Full Diagnostic"** button
   - This runs the automated script: `docs/run_full_diagnostic.sh`
   - Takes 2-5 minutes depending on system size
   - Shows color-coded results (green/yellow/red)

2. **Review the Results**
   - ✅ **Green** = Pass
   - ⚠️ **Yellow** = Warning (needs attention but not critical)
   - ❌ **Red** = Fail (needs immediate action)

3. **Follow the Recommendations**
   - Each failed check includes a link to the relevant documentation
   - Click the link to see detailed fix instructions

### Option 2: Manual Step-by-Step Diagnostic

1. **Follow the 15-Step Checklist**
   - Start with **Phase 1: Service Health** (most critical)
   - Work through each phase in order
   - Each step includes:
     - Command to run
     - What to look for
     - Where to go if issues are found

2. **Use Decision Trees**
   - If you know what's broken, use the decision tree
   - Routes you directly to the relevant documentation

---

## 🔍 Diagnostic Phases

### Phase 1: Service Health (CRITICAL - Start Here)
- ✅ Step 1: Is the Service Running?
- ✅ Step 2: Is Port 8000 Listening?
- ✅ Step 3: Can We Reach FastAPI Directly?

**Why start here?** Most issues are caused by the service not running or crashing.

### Phase 2: CORS Configuration
- ✅ Step 4: CORS Diagnostic

**Common issues:** Wildcard origins with credentials, service not running, nginx interference.

### Phase 3: Code Health
- ✅ Step 5: Syntax Errors Check
- ✅ Step 6: Import Validation
- ✅ Step 7: main.py Structure Validation

**Why important?** Syntax errors prevent service startup. Invalid structure causes runtime errors.

### Phase 4: Router & Endpoints
- ✅ Step 8: Router Inclusion Check
- ✅ Step 9: Endpoint Response Test

**Why important?** Missing routers mean endpoints don't work. Invalid endpoints cause 404 errors.

### Phase 5: Database & Configuration
- ✅ Step 10: Database Connectivity
- ✅ Step 11: Environment Configuration

**Why important?** Database issues prevent data operations. Missing .env file prevents service startup.

### Phase 6: Nginx & External Access
- ✅ Step 12: Nginx Configuration
- ✅ Step 13: External Access Test

**Why important?** Nginx errors prevent external access. Invalid config breaks the site.

### Phase 7: Recent Errors & Logs
- ✅ Step 14: Recent Error Check

**Why important?** Recent errors indicate active problems that need immediate attention.

---

## 🚀 Quick Actions

### Run Specific Diagnostic
- **CORS Issues:** Click "Diagnose CORS" → Routes to CORS Emergency Net
- **Syntax Errors:** Click "Check Syntax" → Routes to Syntax Checking guide
- **Service Status:** Click "Check Service" → Shows service status and logs

### Access Documentation
- **Emergency Nets:** Links to frontend and backend emergency procedures
- **Guardrails:** Links to CORS, syntax, and refactoring guides
- **Testing Checklists:** Links to feature and infrastructure testing guides

---

## 📚 Documentation Reference

### Emergency Procedures
- **Backend Emergency Net:** Critical issues, service won't start, database problems
- **CORS Emergency Net:** CORS configuration fixes, wildcard origin issues

### Guardrails
- **CORS Quick Reference:** One-page CORS cheat sheet
- **Syntax Checking:** How to find and fix syntax errors
- **Refactoring Guide:** Safe code refactoring procedures

### Testing
- **Feature Testing Checklist:** Test all features after changes
- **Infrastructure Testing:** Test system health after deployment

### Diagnostic Scripts
- **run_full_diagnostic.sh:** Automated full system check
- **diagnose_cors.sh:** Comprehensive CORS diagnostic
- **fix_cors_wildcard.sh:** Auto-fix wildcard CORS issue

---

## ⚠️ Common Issues & Quick Fixes

### Service Won't Start
1. Check syntax errors: `bash find_all_syntax_errors.sh`
2. Check logs: `sudo journalctl -u vernal-agents --since "5 minutes ago"`
3. Route to: Backend Emergency Net → "Service Won't Start"

### CORS Errors
1. Run CORS diagnostic: `bash scripts/diagnose_cors.sh`
2. If wildcard issue: `bash scripts/fix_cors_wildcard.sh`
3. Route to: CORS Emergency Net

### 404 Errors (Endpoints Not Found)
1. Check router inclusion: Verify all routers in `main.py`
2. Check endpoint paths: Verify route definitions
3. Route to: Refactoring Guide → Router Extraction

### Database Connection Errors
1. Check .env file exists and has correct credentials
2. Verify database server is accessible
3. Route to: Backend Emergency Net → "Database Issues"

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

## 📝 Best Practices

1. **Run diagnostics before deployment** - Catch issues early
2. **Run diagnostics after deployment** - Verify everything works
3. **Start with Phase 1** - Most issues are service-related
4. **Follow the routes** - Each step routes to detailed documentation
5. **Use automated script** - Faster and more comprehensive than manual checks

---

## 🔗 Related Documentation

- [Master Diagnostic Router](./MASTER_DIAGNOSTIC_ROUTER.md) - Complete diagnostic guide
- [Documentation Index](./DOCUMENTATION_INDEX.md) - All documentation
- [Backend Emergency Net](./EMERGENCY_NET_BACKEND.md) - Critical issues
- [CORS Emergency Net](../guardrails/CORS_EMERGENCY_NET.md) - CORS fixes

---

**Last Updated:** 2025-01-16  
**Maintained by:** Development Team  
**Purpose:** Admin-friendly guide for using the diagnostic system

