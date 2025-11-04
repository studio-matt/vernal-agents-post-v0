#!/usr/bin/env python3
"""
Comprehensive dependency checker - verifies ALL packages from requirements.txt are installed
This is more robust than checking specific packages one by one.
"""

import re
import sys
import subprocess
from pathlib import Path

def parse_requirements(requirements_file):
    """Parse requirements.txt and extract package names and versions"""
    packages = []
    
    with open(requirements_file, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Skip section headers
            if line.startswith('==='):
                continue
            
            # Parse package spec (e.g., "fastapi>=0.104.1", "beautifulsoup4>=4.12.3")
            # Extract package name (before >=, ==, <, >, etc.)
            match = re.match(r'^([a-zA-Z0-9_-]+[a-zA-Z0-9_.-]*)', line)
            if match:
                package_name = match.group(1).lower()
                # Handle extras like "uvicorn[standard]"
                if '[' in package_name:
                    package_name = package_name.split('[')[0]
                packages.append({
                    'name': package_name,
                    'spec': line,
                    'original': line
                })
    
    return packages

def check_package_installed(package_name):
    """Check if a package is installed and importable"""
    try:
        # Try to import the package
        # Handle special cases (e.g., "python-dotenv" -> "dotenv")
        import_name = package_name.replace('-', '_')
        
        # Special cases
        if import_name == 'python_dotenv':
            import_name = 'dotenv'
        elif import_name == 'python_multipart':
            import_name = 'multipart'
        elif import_name == 'python_pptx':
            import_name = 'pptx'
        elif import_name == 'python_jose':
            import_name = 'jose'
        
        __import__(import_name)
        return True, None
    except ImportError as e:
        return False, str(e)
    except Exception as e:
        # Some packages might fail to import for other reasons (e.g., missing system deps)
        # But if we can import it, it's installed
        return True, None

def check_all_dependencies(requirements_file=None):
    """Check all dependencies from requirements.txt"""
    if requirements_file is None:
        # Find requirements.txt in current directory or parent
        script_dir = Path(__file__).parent
        repo_root = script_dir.parent
        requirements_file = repo_root / 'requirements.txt'
    
    if not requirements_file.exists():
        print(f"❌ requirements.txt not found at {requirements_file}")
        return False
    
    print(f"📋 Checking dependencies from {requirements_file}")
    print("=" * 60)
    
    packages = parse_requirements(requirements_file)
    print(f"Found {len(packages)} packages to check\n")
    
    missing = []
    installed = []
    warnings = []
    
    for pkg in packages:
        package_name = pkg['name']
        is_installed, error = check_package_installed(package_name)
        
        if is_installed:
            installed.append(package_name)
            print(f"✅ {package_name}")
        else:
            missing.append({
                'name': package_name,
                'spec': pkg['spec'],
                'error': error
            })
            print(f"❌ {package_name} - NOT INSTALLED")
            if error:
                print(f"   Error: {error}")
    
    print("\n" + "=" * 60)
    print(f"📊 Summary:")
    print(f"   ✅ Installed: {len(installed)}")
    print(f"   ❌ Missing: {len(missing)}")
    
    if missing:
        print(f"\n❌ Missing packages:")
        for pkg in missing:
            print(f"   - {pkg['name']} ({pkg['spec']})")
        
        print(f"\n💡 To install missing packages:")
        print(f"   cd /home/ubuntu/vernal-agents-post-v0")
        print(f"   source venv/bin/activate")
        print(f"   pip install -r requirements.txt")
        print(f"\n   Or install individually:")
        for pkg in missing:
            print(f"   pip install {pkg['spec']}")
        
        return False
    else:
        print(f"\n✅ All dependencies are installed!")
        return True

if __name__ == '__main__':
    success = check_all_dependencies()
    sys.exit(0 if success else 1)

