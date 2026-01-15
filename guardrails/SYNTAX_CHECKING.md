# Syntax Error Detection Guardrails

## Overview

After experiencing multiple syntax errors during refactoring that prevented service startup, we've created comprehensive tools to detect ALL syntax errors at once, rather than fixing them one at a time.

## Tools

### 1. `find_all_syntax_errors.sh`

**Location:** `/home/ubuntu/vernal-agents-post-v0/find_all_syntax_errors.sh`

**Purpose:** Comprehensive syntax checker that uses Python's `py_compile` to check all Python files and tests the full import.

**Usage:**
```bash
cd /home/ubuntu/vernal-agents-post-v0
bash find_all_syntax_errors.sh
```

**What it checks:**
- ✅ `main.py` syntax
- ✅ All `app/routes/*.py` files
- ✅ All other Python files in `app/`
- ✅ Full import test (catches import-time errors like missing imports)

**Output:**
- Lists all files with syntax errors
- Shows the exact error message for each file
- Tests full import to catch runtime import errors
- Provides summary count of errors found

### 2. `scripts/check_syntax_patterns.py`

**Location:** `/home/ubuntu/vernal-agents-post-v0/scripts/check_syntax_patterns.py`

**Purpose:** Advanced pattern checker that finds common syntax error patterns that might not be caught by `py_compile` alone.

**Usage:**
```bash
cd /home/ubuntu/vernal-agents-post-v0
python3 scripts/check_syntax_patterns.py
```

**What it checks:**
- Unmatched try/except/finally blocks
- Orphaned except blocks (without matching try)
- Incomplete dictionary/list/tuple definitions
- Common refactoring issues (orphaned code)

**Note:** This tool may produce false positives for nested try blocks, which are valid Python. Use it as a guide, not as the final authority.

## When to Use

### Before Deployment
Always run both tools before deploying code changes:
```bash
cd /home/ubuntu/vernal-agents-post-v0
git pull origin main
bash find_all_syntax_errors.sh
python3 scripts/check_syntax_patterns.py
```

### After Refactoring
Especially important after:
- Extracting code to new files
- Moving functions between files
- Renaming modules
- Any large-scale code reorganization

### When Service Won't Start
If the service fails to start with syntax errors, run these tools to find ALL errors at once rather than fixing them one-by-one.

## Common Syntax Errors Found

Based on our experience, the most common syntax errors during refactoring are:

1. **Orphaned closing braces** - Leftover `}` from incomplete refactoring
2. **Incomplete try/except/finally blocks** - Missing `except` or `finally` after `try`
3. **Incomplete dictionary definitions** - Dictionary opened with `{` but never closed
4. **Missing imports** - Functions/classes used but not imported (caught by full import test)
5. **Orphaned code** - Code left behind during extraction that breaks syntax

## Integration with EMERGENCY_NET.md

**IMPORTANT**: When `docs/EMERGENCY_NET.md` exists, add a reference to this document in the troubleshooting section:

```markdown
## Syntax Errors Preventing Service Startup

**ALWAYS RUN FIRST**: Before debugging individual errors, run the comprehensive syntax checkers:

```bash
cd /home/ubuntu/vernal-agents-post-v0
bash find_all_syntax_errors.sh
python3 scripts/check_syntax_patterns.py
```

See `guardrails/SYNTAX_CHECKING.md` for full documentation.

This will find ALL syntax errors at once, preventing the circuitous one-at-a-time debugging process.
```

When diagnosing service startup failures, always run these tools first.

## Example Output

```
==========================================
COMPREHENSIVE SYNTAX ERROR CHECK
==========================================

=== Checking main.py ===
✅ main.py syntax OK

=== Checking app/routes/*.py ===
✅ app/routes/admin.py syntax OK
❌ app/routes/platforms.py
   File "app/routes/platforms.py", line 1626
     params = {
              ^
SyntaxError: '{' was never closed

=== Testing full import ===
❌ Full import FAILED!
   NameError: name 'Request' is not defined

==========================================
SUMMARY
==========================================
❌ Found 1 file(s) with syntax errors
```

## Best Practices

1. **Run before committing** - Catch errors early
2. **Run after pulling** - Verify code is valid before restarting service
3. **Fix all errors at once** - Don't fix one at a time, fix them all
4. **Verify after fixes** - Run again to ensure all errors are resolved

## Maintenance

These tools should be updated if:
- New file patterns emerge (e.g., new directories)
- New syntax error patterns are discovered
- Python version changes require different checks

