#!/usr/bin/env python3
"""
Fix the main.py import error on production server
"""
import re

def fix_main_py():
    # Read the current main.py
    with open('main.py', 'r') as f:
        content = f.read()
    
    # Fix the problematic import line
    # Look for the line with Campaign, RawData, MachineContent imports
    pattern = r'from database import DatabaseManager1, engine, Base, Campaign, RawData, MachineContent'
    replacement = 'from database import DatabaseManager1, engine, Base'
    
    # Replace the problematic import
    fixed_content = re.sub(pattern, replacement, content)
    
    # Write the fixed content back
    with open('main.py', 'w') as f:
        f.write(fixed_content)
    
    print("✅ Fixed main.py - removed problematic imports")
    print("✅ Campaign, RawData, MachineContent imports removed")

if __name__ == "__main__":
    fix_main_py()
