"""
Code Health Scanner - Detects files exceeding LOC threshold.

Scans Python files in the codebase and identifies files that exceed
the configured line count threshold (default 3000).
Excludes paths that would be ignored by .gitignore and system/dependency
paths (e.g. /home/ubuntu/*, site-packages) so only "our" code is considered.
"""

import os
import json
import subprocess
import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Path prefixes and segments that indicate non-repo / system code (excluded from guard rails)
NON_REPO_PATH_PREFIXES = ("/home/ubuntu/",)
NON_REPO_PATH_SEGMENTS = ("site-packages", "vernal_env", "vernal-env", ".venv")

# Default threshold: 3000 lines
DEFAULT_LOC_THRESHOLD = int(os.getenv("CODE_HEALTH_LOC_THRESHOLD", "3000"))
ENABLE_PYLINT = os.getenv("CODE_HEALTH_ENABLE_PYLINT", "0") == "1"
PYLINT_TARGETS = os.getenv("CODE_HEALTH_PYLINT_TARGETS", "").split(",") if os.getenv("CODE_HEALTH_PYLINT_TARGETS") else []


def _load_gitignore_patterns(root_path: Path) -> List[str]:
    """Load .gitignore patterns from repo root (and optional subdir .gitignore)."""
    patterns: List[str] = []
    gitignore_path = root_path / ".gitignore"
    if not gitignore_path.is_file():
        return patterns
    try:
        with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                patterns.append(line)
    except Exception as e:
        logger.warning(f"Could not read .gitignore at {gitignore_path}: {e}")
    return patterns


def _path_matches_gitignore(file_path: Path, root_path: Path, patterns: List[str]) -> bool:
    """
    Return True if file_path should be ignored according to .gitignore-style patterns.
    Uses simple fnmatch-style matching; ** is treated as match-any number of path segments.
    """
    try:
        rel = file_path.resolve().relative_to(root_path.resolve())
    except ValueError:
        return False
    rel_parts = rel.parts
    rel_str = str(rel).replace("\\", "/")

    for raw in patterns:
        p = raw.strip()
        if not p or p.startswith("#"):
            continue
        if p.endswith("/"):
            p = p[:-1]
        if p.startswith("/"):
            p = p[1:]
        match_pattern = p.replace("**", "*")
        if fnmatch.fnmatch(rel_str, match_pattern):
            return True
        if fnmatch.fnmatch(rel_str, f"**/{match_pattern}"):
            return True
        if "/" not in match_pattern and any(fnmatch.fnmatch(part, match_pattern) for part in rel_parts):
            return True
    return False


def _should_skip_path(file_path: Path, root_path: Path, gitignore_patterns: List[str]) -> bool:
    """Return True if this path should be excluded from scanning (non-repo / gitignored)."""
    path_str = str(file_path)
    if any(path_str.startswith(prefix) for prefix in NON_REPO_PATH_PREFIXES):
        return True
    if any(seg in file_path.parts for seg in NON_REPO_PATH_SEGMENTS):
        return True
    if gitignore_patterns and _path_matches_gitignore(file_path, root_path, gitignore_patterns):
        return True
    return False


def count_lines(file_path: Path) -> int:
    """
    Count lines of code in a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Number of lines in the file
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return len(f.readlines())
    except Exception as e:
        logger.warning(f"Could not read {file_path}: {e}")
        return 0


def scan_file(file_path: Path, threshold: int = DEFAULT_LOC_THRESHOLD) -> Optional[Dict[str, Any]]:
    """
    Scan a single file and return violation if it exceeds threshold.
    
    Args:
        file_path: Path to the file to scan
        threshold: Maximum allowed lines of code
        
    Returns:
        Dictionary with violation details or None if file is OK
    """
    loc = count_lines(file_path)
    
    if loc > threshold:
        return {
            "file": str(file_path),
            "lines": loc,
            "threshold": threshold,
            "excess": loc - threshold,
        }
    
    return None


def scan_codebase(
    root_dir: Optional[str] = None,
    threshold: int = DEFAULT_LOC_THRESHOLD,
    exclude_dirs: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Scan codebase for files exceeding LOC threshold.
    
    Args:
        root_dir: Root directory to scan (default: current working directory)
        threshold: Maximum allowed lines of code per file
        exclude_dirs: List of directory names to exclude (e.g., ['node_modules', '__pycache__'])
        
    Returns:
        Dictionary with scan results
    """
    if root_dir is None:
        root_dir = os.getcwd()
    
    if exclude_dirs is None:
        exclude_dirs = [
            'node_modules', '__pycache__', '.git', '.next', 'venv', 'env',
            'backend-repo', 'backend-repo-git', 'backend-repo-temp',
            'temp-agents-fix', 'temp-agents-fix2', 'temp-agents-repo',
            'temp-api', 'temp-pages', '.local', 'dist', 'build',
            '.refactor_backups',  # Refactoring backups
        ]
    
    root_path = Path(root_dir)
    violations = []
    scanned_files = []

    # Load .gitignore once so we only scan repo-tracked code (exclude gitignored + non-repo paths)
    gitignore_patterns = _load_gitignore_patterns(root_path)

    # Scan Python files
    for py_file in root_path.rglob("*.py"):
        # Skip paths that are non-repo (e.g. /home/ubuntu/*, site-packages) or gitignored
        if _should_skip_path(py_file, root_path, gitignore_patterns):
            continue

        # Skip excluded directories
        if any(excluded in py_file.parts for excluded in exclude_dirs):
            continue

        # Skip backup directories (pattern: *-bak-* or *-backup-*)
        file_path_str = str(py_file)
        if '-bak-' in file_path_str or '-backup-' in file_path_str or file_path_str.endswith('.bak'):
            continue

        # Skip if in a hidden directory
        if any(part.startswith('.') and part != '.' for part in py_file.parts):
            continue

        scanned_files.append(str(py_file))
        violation = scan_file(py_file, threshold)
        if violation:
            violations.append(violation)
    
    # Sort violations by excess lines (worst offenders first)
    violations.sort(key=lambda x: x['excess'], reverse=True)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "threshold": threshold,
        "total_files_scanned": len(scanned_files),
        "violations": violations,
        "violation_count": len(violations),
        "scanned_files": scanned_files[:100],  # Limit to first 100 for JSON size
    }


def run_pylint(file_path: str) -> Dict[str, Any]:
    """
    Run pylint on a file and return results.
    
    Args:
        file_path: Path to the file to lint
        
    Returns:
        Dictionary with pylint results
    """
    try:
        result = subprocess.run(
            ["pylint", file_path, "--output-format=json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if result.returncode == 0:
            return {"status": "ok", "issues": []}
        
        # Parse JSON output
        try:
            issues = json.loads(result.stdout) if result.stdout else []
            return {
                "status": "issues_found",
                "issues": issues,
                "issue_count": len(issues),
            }
        except json.JSONDecodeError:
            return {
                "status": "error",
                "error": "Failed to parse pylint output",
                "raw_output": result.stdout[:500],
            }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "error": "Pylint timed out"}
    except FileNotFoundError:
        return {"status": "not_available", "error": "pylint not installed"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def generate_refactor_prompt(file_path: str, lines: int, threshold: int, constraints: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate a refactor prompt with backup procedures and constraints.
    
    Args:
        file_path: Path to the file that needs refactoring
        lines: Current line count
        threshold: Maximum allowed lines
        constraints: Optional constraints dictionary
        
    Returns:
        Formatted refactor prompt string
    """
    excess = lines - threshold
    file_name = os.path.basename(file_path)
    
    prompt = f"""# Refactor Task: {file_name}

## File Information
- **File:** `{file_path}`
- **Current Lines:** {lines}
- **Threshold:** {threshold}
- **Excess:** +{excess} lines

## CRITICAL: Backup Before Refactoring

**STEP 1: Create Backup (REQUIRED)**
```bash
cd /home/ubuntu/vernal-agents-post-v0
bash guardrails/backup_before_refactor.sh {file_path}
```

This saves the original file to `.refactor_backups/[timestamp]/` for comparison later.

## Refactoring Constraints

### Non-Negotiable Constraints:
1. **API contracts must remain identical** - All endpoints must work exactly the same
2. **Runtime configuration unchanged** - No changes to how the app starts or configures
3. **Entrypoint behavior preserved** - If this is `main.py`, it must remain a thin entry point (see `guardrails/REFACTORING.md`)
4. **No rewrites, only move/split/refactor** - Move code, don't rewrite logic
5. **CRITICAL: Never delete `main.py`** - It must remain as a thin entry point with router includes

### Do NOT Modify:
- Authentication/authorization logic
- Scheduler configuration  
- Database connection lifecycle
- System settings semantics
- Guardrails behavior/thresholds
- CORS middleware configuration (if in main.py)

### STOP Condition:
- **HALT immediately** if refactor would touch protected areas listed above
- **HALT** if refactor would break API contracts
- **HALT** if refactor would change entrypoint behavior

## Refactoring Strategy

1. **Create `app/` package structure** (if not exists):
   - `app/routes/` for route modules
   - `app/schemas/` for Pydantic models
   - `app/services/` for business logic
   - `app/utils/` for helper functions

2. **One module at a time:**
   - Extract one logical group of functions
   - Test after each extraction
   - Don't extract multiple features at once

3. **Package boundary pinning:**
   - Maintain clear separation between routes, services, schemas
   - Use proper imports: `from app.routes.{feature} import {feature}_router`

4. **Router parity checks:**
   - Ensure all routes are included in `main.py`
   - Verify route decorators match original endpoints
   - Test each endpoint after extraction

## Step-by-Step Refactoring Process

### Before Starting:
1. ✅ **Create backup:** `bash guardrails/backup_before_refactor.sh {file_path}`
2. ✅ Run syntax check: `bash find_all_syntax_errors.sh`
3. ✅ Verify service is running: `curl http://127.0.0.1:8000/health`

### During Refactoring:
1. Extract functions to appropriate module (routes/services/utils)
2. Create router if extracting routes: `{feature}_router = APIRouter()`
3. Add route decorators: `@{feature}_router.get/post/put/delete`
4. Import router in `main.py`: `from app.routes.{feature} import {feature}_router`
5. Include router: `app.include_router({feature}_router)`
6. **Remove duplicate code from original file** ⚠️

### After Refactoring:
1. ✅ **Compare with backup:** `bash guardrails/compare_refactor.sh`
   - Shows what changed (added/removed/modified)
   - Fastest way to diff old monolith vs new refactor
   - Track code snippets to find why things broke
2. ✅ Run syntax check: `bash find_all_syntax_errors.sh`
3. ✅ Verify structure: `bash guardrails/validate_main_structure.sh`
4. ✅ Test import: `python3 -c "import main; print('✅ Import successful')"`
5. ✅ Restart service: `sudo systemctl restart vernal-agents`
6. ✅ Verify health: `curl http://127.0.0.1:8000/health`
7. ✅ Test endpoints from extracted router

### If Issues Found:
- **Compare with backup:** `bash guardrails/compare_refactor.sh [timestamp]`
- **See detailed diff:** `diff -u .refactor_backups/[timestamp]/{file_path} {file_path}`
- **Restore if needed:** `bash guardrails/restore_from_backup.sh [timestamp] {file_path}`

## Verification Steps

1. **Compile check:**
   ```bash
   python3 -m py_compile {file_path}
   ```

2. **Import test:**
   ```bash
   python3 -c "import sys; sys.path.insert(0, '.'); import {file_name.replace('.py', '')}"
   ```

3. **Route table verification:**
   - Check all routes are included in `main.py`
   - Verify no duplicate endpoint definitions

4. **Service boot test:**
   ```bash
   sudo systemctl restart vernal-agents
   sudo systemctl status vernal-agents
   curl http://127.0.0.1:8000/health
   ```

## Deliverable

- ✅ Reduce file below {threshold} lines
- ✅ Add migration map at top of extracted file showing what was moved
- ✅ All tests pass
- ✅ Service starts successfully
- ✅ All endpoints work identically to before

## Documentation References

- **Refactoring Guide:** `guardrails/REFACTORING.md` - Complete refactoring procedures
- **Syntax Checking:** `guardrails/SYNTAX_CHECKING.md` - Fix syntax errors
- **Master Diagnostic:** `docs/MASTER_DIAGNOSTIC_ROUTER.md` - Complete system check
- **Backup Tools:** 
  - `guardrails/backup_before_refactor.sh` - Create backup
  - `guardrails/compare_refactor.sh` - Compare old vs new
  - `guardrails/restore_from_backup.sh` - Restore from backup

## Important Notes

- **Always backup first** - Enables fast debugging by comparing old vs new
- **One module at a time** - Don't extract multiple features simultaneously  
- **Test after each step** - Catch issues early
- **Use comparison tools** - Fastest way to find what broke
- **Follow guardrails** - Prevents common mistakes

---

**Ready to refactor? Start with the backup command above, then proceed step-by-step.**
"""
    
    # Add custom constraints if provided
    if constraints:
        prompt += "\n## Additional Constraints\n\n"
        for key, value in constraints.items():
            prompt += f"- **{key}:** {value}\n"
    
    return prompt


def generate_reports(scan_results: Dict[str, Any], output_dir: str = "reports") -> Dict[str, str]:
    """
    Generate JSON and Markdown reports from scan results.
    
    Args:
        scan_results: Results from scan_codebase()
        output_dir: Directory to write reports to
        
    Returns:
        Dictionary with paths to generated reports
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate JSON report
    json_path = os.path.join(output_dir, "code_health.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(scan_results, f, indent=2)
    
    # Generate Markdown report
    md_path = os.path.join(output_dir, "code_health.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Code Health Report\n\n")
        f.write(f"**Generated:** {scan_results['timestamp']}\n\n")
        f.write(f"**Threshold:** {scan_results['threshold']} lines per file\n\n")
        f.write(f"**Files Scanned:** {scan_results['total_files_scanned']}\n\n")
        f.write(f"**Violations Found:** {scan_results['violation_count']}\n\n")
        
        if scan_results['violations']:
            f.write("## Files Exceeding Threshold\n\n")
            f.write("| File | Lines | Excess |\n")
            f.write("|------|-------|--------|\n")
            
            for violation in scan_results['violations']:
                file_name = violation['file']
                lines = violation['lines']
                excess = violation['excess']
                f.write(f"| `{file_name}` | {lines} | +{excess} |\n")
        else:
            f.write("## ✅ No Violations Found\n\n")
            f.write("All files are within the threshold.\n")
    
    return {
        "json": json_path,
        "markdown": md_path,
    }

