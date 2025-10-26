# 🛠️ Systematic Dependency Management

## The Problem
We've been hitting dependency issues in CI/CD because we're not systematically testing requirements before deployment. This leads to:
- Package version conflicts
- Missing packages on PyPI
- Docker build failures
- Status 137 errors from dependency resolution

## The Solution: Systematic Dependency Audit

### 1. 🔍 Pre-Deployment Dependency Check
**Run this BEFORE every deployment:**

```bash
# On your local machine (not CI)
cd /path/to/backend-repo

# Install pip-tools for dependency management
pip install pip-tools

# Test all requirements files
pip install -r requirements-core.txt
pip install -r requirements-ai.txt  
pip install -r requirements-remaining.txt

# Check for broken dependencies
pip check

# Test Docker build locally
docker build -f Dockerfile.deploy -t vernal-agents-test .
docker rmi vernal-agents-test
```

### 2. 📋 Automated CI Dependency Check
**We've added a GitHub Action that runs before deployment:**

- **File:** `.github/workflows/dependency-check.yml`
- **Triggers:** On PR changes to requirements files, manual trigger
- **What it does:**
  - Installs all requirements
  - Runs `pip check` for broken dependencies
  - Tests Docker build
  - Creates locked requirements file
  - Fails if any issues found

### 3. 🔧 Dependency Resolution Process

#### Step 1: Remove Version Pins (Temporarily)
```bash
# Create test files without version pins
sed 's/==[0-9].*//g' requirements-core.txt > test-core.txt
sed 's/==[0-9].*//g' requirements-ai.txt > test-ai.txt
sed 's/==[0-9].*//g' requirements-remaining.txt > test-remaining.txt

# Test what versions resolve
pip install -r test-core.txt -r test-ai.txt -r test-remaining.txt
```

#### Step 2: Create Locked Requirements
```bash
# Combine all requirements
cat requirements-core.txt requirements-ai.txt requirements-remaining.txt > requirements-combined.txt

# Remove duplicates and create clean input
sort requirements-combined.txt | uniq > requirements-clean.txt

# Create locked requirements
pip-compile requirements-clean.txt --output-file requirements-locked.txt
```

#### Step 3: Test Everything
```bash
# Test the locked requirements
pip install -r requirements-locked.txt
pip check

# Test Docker build
docker build -f Dockerfile.deploy -t vernal-agents-test .
```

### 4. 🚨 Common Issues and Fixes

#### Issue: Package Version Not Found
```bash
# Error: Could not find a version that satisfies the requirement browser-use==0.0.1
# Fix: Check available versions
pip index versions browser-use
# Update to valid version: browser-use==0.1.0
```

#### Issue: Dependency Conflicts
```bash
# Error: pip check shows conflicts
# Fix: Remove conflicting version pins, let pip resolve
# Or: Use pip-compile to find compatible versions
```

#### Issue: Docker Build Fails
```bash
# Fix: Test Docker build locally first
docker build -f Dockerfile.deploy -t test .
# Fix any issues before pushing to CI
```

### 5. 📁 Files Created

- **`audit_dependencies.sh`** - Complete dependency audit script
- **`check_requirements.py`** - Python script to check package availability
- **`requirements-minimal.txt`** - Minimal requirements without version pins
- **`.github/workflows/dependency-check.yml`** - CI dependency check
- **`requirements-locked.txt`** - Generated locked requirements (after running pip-compile)

### 6. 🎯 Workflow

1. **Before making changes:** Run `./audit_dependencies.sh`
2. **Before committing:** Ensure all requirements install locally
3. **Before deploying:** CI will run dependency check automatically
4. **If issues found:** Fix locally, then retry

### 7. 🏆 Benefits

- ✅ **Catch ALL dependency issues before CI/CD**
- ✅ **No more "corner-case" surprises**
- ✅ **Faster deployments** (no failed builds)
- ✅ **Reproducible builds** with locked requirements
- ✅ **Systematic approach** instead of reactive fixes

### 8. 🚨 Common Dependency Issues

#### Issue: "No matching distribution found"
**Root Cause:** Pinned version doesn't exist for your Python/base image  
**Fix:** Use flexible version pins (e.g., `cryptography>=46.0.0` instead of `==41.0.8`)  
**Prevention:** Always test pinned versions in Docker before committing

#### Issue: "Dependency conflict"  
**Root Cause:** Two packages require incompatible versions (e.g., `python-dotenv==1.0.0` vs `browser-use requires >=1.0.1`)  
**Fix:** Update to compatible versions (e.g., `python-dotenv>=1.0.1`) or use flexible pins  
**Prevention:** Run `pip check` after every requirements change  
**Example:** `python-dotenv==1.0.0` conflicts with `browser-use==0.1.0` which requires `>=1.0.1`

#### Issue: "Python version mismatch"
**Root Cause:** Package built for different Python version  
**Fix:** Use Python 3.11 base image, upgrade build tools  
**Prevention:** Specify Python version in all workflows

## Quick Start

```bash
# 1. Test everything locally
./audit_dependencies.sh

# 2. If issues found, fix them
# 3. Commit and push
# 4. CI will verify before deployment
```

**This systematic approach prevents the dependency nightmare and makes deployments bulletproof!**
