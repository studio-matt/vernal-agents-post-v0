#!/usr/bin/env python3
"""
Dependency Validation Script
Ensures no dependency conflicts exist before deployment.

This script:
1. Validates requirements.in uses proper lower bounds (>=)
2. Attempts to resolve all dependencies
3. Checks for known conflict patterns
4. Verifies pip-tools compatibility
"""

import sys
import subprocess
import re
from pathlib import Path

def check_pip_version():
    """Ensure pip version is compatible with pip-tools"""
    result = subprocess.run(
        [sys.executable, '-m', 'pip', '--version'],
        capture_output=True,
        text=True
    )
    version_str = result.stdout.strip()
    # Extract version number
    match = re.search(r'pip (\d+)\.', version_str)
    if match:
        major_version = int(match.group(1))
        if major_version >= 25:
            print(f"⚠️  WARNING: pip {major_version}.x detected. pip-tools 7.x requires pip<25.0")
            print("   This will cause: AttributeError: 'InstallRequirement' object has no attribute 'use_pep517'")
            return False
    print(f"✅ pip version compatible: {version_str}")
    return True

def validate_requirements_in(file_path):
    """Validate requirements.in follows best practices"""
    issues = []
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines, 1):
        line = line.strip()
        # Skip comments and empty lines
        if not line or line.startswith('#'):
            continue
        
        # Check for exact pins (==) - should use >= instead
        if re.match(r'^[a-zA-Z0-9_-]+==', line):
            issues.append(f"Line {i}: Exact pin detected: {line}")
            issues.append(f"   Should use: {line.replace('==', '>=')}")
        
        # Check for unpinned packages (no version constraint)
        if re.match(r'^[a-zA-Z0-9_-]+$', line.split('#')[0].strip()):
            issues.append(f"Line {i}: Unpinned package: {line}")
            issues.append(f"   Should specify minimum version: {line.split('#')[0].strip()}>=")
    
    if issues:
        print("❌ requirements.in validation issues:")
        for issue in issues:
            print(f"   {issue}")
        return False
    else:
        print("✅ requirements.in follows best practices (lower bounds only)")
        return True

def test_dependency_resolution(file_path):
    """Test if dependencies can be resolved"""
    print(f"\n🧪 Testing dependency resolution for {file_path}...")
    
    # Create temporary venv for testing
    import tempfile
    import venv
    
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = Path(tmpdir) / 'test_venv'
        venv.create(venv_path, with_pip=True)
        
        # Get pip executable
        if sys.platform == 'win32':
            pip_exe = venv_path / 'Scripts' / 'pip'
        else:
            pip_exe = venv_path / 'bin' / 'pip'
        
        # Install pip-tools with pip<25.0
        print("   Installing pip-tools with pip<25.0...")
        subprocess.run(
            [str(pip_exe), 'install', 'pip<25.0', 'setuptools', 'wheel', 'pip-tools'],
            check=True,
            capture_output=True
        )
        
        # Try to compile requirements
        print("   Attempting pip-compile...")
        try:
            result = subprocess.run(
                [str(venv_path / 'bin' / 'python'), '-m', 'piptools', 'compile', 
                 str(file_path), '--output-file', str(Path(tmpdir) / 'test-locked.txt')],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                print("❌ Dependency resolution FAILED:")
                print(result.stderr)
                return False
            else:
                print("✅ Dependency resolution successful")
                return True
        except subprocess.TimeoutExpired:
            print("❌ Dependency resolution TIMED OUT (>120s)")
            return False
        except Exception as e:
            print(f"❌ Error during dependency resolution: {e}")
            return False

def check_known_conflicts(file_path):
    """Check for known dependency conflict patterns"""
    known_conflicts = [
        (r'crewai\s*[<>=]+\s*0\.24', 'crewai<0.24 requires langchain-core<0.4.0, conflicts with browser-use'),
        (r'anthropic\s*==\s*0\.7\.8', 'anthropic==0.7.8 conflicts with langchain-anthropic'),
        (r'requests\s*==\s*2\.31\.0', 'requests==2.31.0 too old for browser-use'),
    ]
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    issues = []
    for pattern, message in known_conflicts:
        if re.search(pattern, content, re.IGNORECASE):
            issues.append(message)
    
    if issues:
        print("⚠️  Known conflict patterns detected:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print("✅ No known conflict patterns detected")
        return True

def main():
    print("🔍 DEPENDENCY VALIDATION SCRIPT")
    print("=" * 50)
    
    requirements_in = Path(__file__).parent / 'requirements.in'
    if not requirements_in.exists():
        print(f"❌ requirements.in not found at {requirements_in}")
        sys.exit(1)
    
    # Run all checks
    checks = [
        ("Pip version compatibility", check_pip_version),
        ("requirements.in best practices", lambda: validate_requirements_in(requirements_in)),
        ("Known conflict patterns", lambda: check_known_conflicts(requirements_in)),
        ("Dependency resolution", lambda: test_dependency_resolution(requirements_in)),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n📋 {name}:")
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 VALIDATION SUMMARY:")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All dependency checks passed! Safe to deploy.")
        sys.exit(0)
    else:
        print("\n🚨 One or more dependency checks FAILED. Fix issues before deploying.")
        sys.exit(1)

if __name__ == '__main__':
    main()

