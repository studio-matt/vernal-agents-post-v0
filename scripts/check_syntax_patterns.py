#!/usr/bin/env python3
"""
Advanced syntax pattern checker
Finds common syntax error patterns that py_compile might miss or report confusingly
"""

import os
import sys
import re
from pathlib import Path

ERRORS = []

def check_file(filepath):
    """Check a single Python file for common syntax error patterns"""
    file_errors = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        return [f"Cannot read file: {e}"]
    
    # Check for common patterns
    in_try = False
    in_except = False
    in_finally = False
    try_line = None
    
    brace_stack = []
    bracket_stack = []
    paren_stack = []
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Track try/except/finally blocks
        if re.match(r'^\s*try\s*:', stripped):
            if in_try and not in_except and not in_finally:
                file_errors.append(f"Line {i}: try block started but previous try (line {try_line}) not closed with except/finally")
            in_try = True
            in_except = False
            in_finally = False
            try_line = i
        elif re.match(r'^\s*except\s+', stripped):
            if not in_try:
                file_errors.append(f"Line {i}: except without matching try")
            in_except = True
        elif re.match(r'^\s*finally\s*:', stripped):
            if not in_try:
                file_errors.append(f"Line {i}: finally without matching try")
            in_finally = True
            in_try = False  # finally closes the try block
        elif in_try and not in_except and not in_finally and stripped and not stripped.startswith('#'):
            # Check if we're still in the try block (not indented under except/finally)
            # This is a heuristic - might have false positives
            pass
        
        # Check for unmatched braces (in strings, this is OK, but we'll flag obvious cases)
        # Count braces, brackets, parentheses (simple check)
        open_braces = line.count('{') - line.count('}')
        open_brackets = line.count('[') - line.count(']')
        open_parens = line.count('(') - line.count(')')
        
        # Check for obvious unmatched patterns
        if stripped.endswith('{') and not any(c in stripped for c in ['"', "'"]):
            # Dictionary opening
            pass
        if stripped == '}' and not any(c in stripped for c in ['"', "'"]):
            # Dictionary closing - check if we have a matching opening
            pass
        
        # Check for incomplete dictionary/list/tuple on last line
        if i == len(lines):
            if stripped.endswith(('{', '[', '(')) and not stripped.endswith(('{{', '[[', '((')):
                # Might be incomplete if it's not a string
                if not any(quote in stripped for quote in ['"', "'"]):
                    file_errors.append(f"Line {i}: File ends with unclosed {{, [, or (")
    
    # Check if try block was never closed
    if in_try and not in_finally:
        file_errors.append(f"Line {try_line}: try block started but never closed with except/finally")
    
    # Check for orphaned code patterns (common refactoring issues)
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Orphaned closing braces
        if stripped == '}' and i > 1:
            prev_stripped = lines[i-2].strip() if i > 1 else ''
            if not prev_stripped.endswith(('{', ',', ':')):
                # Might be orphaned
                pass
        # Orphaned except without try
        if re.match(r'^\s*except\s+', stripped) and i > 1:
            # Check if there's a try above
            found_try = False
            for j in range(max(0, i-20), i-1):
                if re.match(r'^\s*try\s*:', lines[j].strip()):
                    found_try = True
                    break
            if not found_try:
                file_errors.append(f"Line {i}: except block without matching try above")
    
    return file_errors

def main():
    """Main function"""
    if len(sys.argv) > 1:
        root_dir = Path(sys.argv[1])
    else:
        root_dir = Path('.')
    
    python_files = []
    
    # Find all Python files
    if (root_dir / 'main.py').exists():
        python_files.append(root_dir / 'main.py')
    
    routes_dir = root_dir / 'app' / 'routes'
    if routes_dir.exists():
        python_files.extend(routes_dir.glob('*.py'))
    
    # Check other app files
    app_dir = root_dir / 'app'
    if app_dir.exists():
        for py_file in app_dir.rglob('*.py'):
            if 'routes' not in str(py_file):
                python_files.append(py_file)
    
    print("=" * 50)
    print("ADVANCED SYNTAX PATTERN CHECK")
    print("=" * 50)
    print()
    
    total_errors = 0
    
    for filepath in sorted(python_files):
        errors = check_file(filepath)
        if errors:
            print(f"❌ {filepath}")
            for error in errors:
                print(f"   {error}")
            print()
            total_errors += len(errors)
        else:
            print(f"✅ {filepath}")
    
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)
    if total_errors == 0:
        print("✅ No pattern errors found")
        return 0
    else:
        print(f"❌ Found {total_errors} potential pattern issue(s)")
        return 1

if __name__ == '__main__':
    sys.exit(main())

