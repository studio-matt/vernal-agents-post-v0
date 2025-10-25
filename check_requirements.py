#!/usr/bin/env python3
"""
Simple dependency checker that validates requirements files
without needing to install packages
"""

import re
import requests
import json

def check_package_exists(package_name, version=None):
    """Check if a package exists on PyPI"""
    try:
        # Clean package name (remove extras like [standard])
        clean_name = re.split(r'[\[\]]', package_name)[0]
        
        url = f"https://pypi.org/pypi/{clean_name}/json"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if version:
                available_versions = list(data['releases'].keys())
                if version in available_versions:
                    return True, f"✅ {package_name}=={version} exists"
                else:
                    return False, f"❌ {package_name}=={version} not found. Available: {available_versions[-5:]}"
            else:
                return True, f"✅ {package_name} exists"
        else:
            return False, f"❌ {package_name} not found on PyPI"
    except Exception as e:
        return False, f"❌ Error checking {package_name}: {str(e)}"

def check_requirements_file(filename):
    """Check all packages in a requirements file"""
    print(f"\n🔍 Checking {filename}...")
    
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
        
        issues = []
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
                
            # Parse package and version
            if '==' in line:
                package, version = line.split('==', 1)
                package = package.strip()
                version = version.strip()
                
                exists, message = check_package_exists(package, version)
                print(f"  Line {line_num}: {message}")
                
                if not exists:
                    issues.append(f"Line {line_num}: {message}")
            else:
                # No version specified
                package = line.strip()
                exists, message = check_package_exists(package)
                print(f"  Line {line_num}: {message}")
                
                if not exists:
                    issues.append(f"Line {line_num}: {message}")
        
        return issues
        
    except FileNotFoundError:
        print(f"❌ File {filename} not found")
        return [f"File {filename} not found"]
    except Exception as e:
        print(f"❌ Error reading {filename}: {str(e)}")
        return [f"Error reading {filename}: {str(e)}"]

def main():
    print("🔍 DEPENDENCY AUDIT - CHECKING PACKAGE AVAILABILITY")
    print("=" * 60)
    
    all_issues = []
    
    # Check all requirements files
    requirements_files = [
        'requirements-core.txt',
        'requirements-ai.txt', 
        'requirements-remaining.txt',
        'requirements.txt'
    ]
    
    for req_file in requirements_files:
        issues = check_requirements_file(req_file)
        all_issues.extend(issues)
    
    print("\n" + "=" * 60)
    
    if all_issues:
        print("❌ ISSUES FOUND:")
        for issue in all_issues:
            print(f"  - {issue}")
        print(f"\nTotal issues: {len(all_issues)}")
        return 1
    else:
        print("✅ ALL PACKAGES ARE AVAILABLE ON PYPI")
        return 0

if __name__ == "__main__":
    exit(main())
