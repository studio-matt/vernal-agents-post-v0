#!/usr/bin/env python3
"""
Comprehensive Python environment and import smoke test for backend reliability.

- Checks Python and pip availability
- Verifies ability to install packages
- Checks for all critical imports (both pip and local modules)
- Fails loudly if any required module is missing
"""

import sys

print("Python version:", sys.version)
print("Python path:", sys.path[:3])

# Test core imports
for mod in ["json", "os", "datetime"]:
    try:
        __import__(mod)
        print(f"✅ {mod} - OK")
    except ImportError as e:
        print(f"❌ {mod} - FAILED:", e)

# Test pip and pip install
try:
    import subprocess
    result = subprocess.run([sys.executable, "-m", "pip", "--version"], 
                          capture_output=True, text=True, timeout=5)
    print("✅ pip available:", result.stdout.strip())
except Exception as e:
    print("❌ pip not available:", e)

try:
    import subprocess
    result = subprocess.run([sys.executable, "-m", "pip", "install", "--user", "requests"], 
                          capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        print("✅ pip install works")
    else:
        print("❌ pip install failed:", result.stderr)
except Exception as e:
    print("❌ pip install error:", e)

# Test project-critical imports
modules_to_test = [
    "fastapi",
    "sqlalchemy",
    "pydantic",
    "tweepy",
    "paramiko",
    "pdfplumber",
    "browser_use",      # Critical - has failed before!
    "agents",
    "tasks",
    "database",
    "models",
    "crewai",
    "tools",
    "httpx",
    # Add more as needed!
]

any_failed = False
for mod in modules_to_test:
    try:
        __import__(mod)
        print(f"✅ {mod} - OK")
    except ImportError as e:
        print(f"❌ {mod} - FAILED: {e}")
        any_failed = True

print("Smoke test complete.")

if any_failed:
    print("❌ One or more critical imports FAILED. Deployment should be blocked.")
    sys.exit(1)
else:
    print("✅ All critical imports passed. Safe to deploy.")
