"""
Code Health Scanner - Detects files exceeding LOC threshold.

Scans Python files in the codebase and identifies files that exceed
the configured line count threshold (default 3000).
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Default threshold: 3000 lines
DEFAULT_LOC_THRESHOLD = int(os.getenv("CODE_HEALTH_LOC_THRESHOLD", "3000"))
ENABLE_PYLINT = os.getenv("CODE_HEALTH_ENABLE_PYLINT", "0") == "1"
PYLINT_TARGETS = os.getenv("CODE_HEALTH_PYLINT_TARGETS", "").split(",") if os.getenv("CODE_HEALTH_PYLINT_TARGETS") else []


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
        ]
    
    root_path = Path(root_dir)
    violations = []
    scanned_files = []
    
    # Scan Python files
    for py_file in root_path.rglob("*.py"):
        # Skip excluded directories
        if any(excluded in py_file.parts for excluded in exclude_dirs):
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

