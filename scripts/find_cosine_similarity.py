#!/usr/bin/env python3
"""
Diagnostic script to locate cosine similarity calculations in the codebase.
Searches for patterns that might indicate where BH-LVT and punctuation cosine are computed.
"""

import os
import re
from pathlib import Path

def search_for_cosine_patterns(root_dir):
    """Search for cosine similarity calculation patterns."""
    patterns = [
        r'cosine',
        r'similarity',
        r'BH.*LVT|LVT.*BH',
        r'punctuation.*cosine|cosine.*punctuation',
        r'weighted.*cosine|cosine.*weighted',
        r'pairwise.*z.*score|z.*score.*pairwise',
        r'standardize|normalize',
        r'scipy.*spatial|sklearn.*metrics',
        r'from scipy|from sklearn|import scipy|import sklearn',
    ]
    
    results = {}
    
    for root, dirs, files in os.walk(root_dir):
        # Skip common directories
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv']]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                        
                        for pattern in patterns:
                            matches = re.finditer(pattern, content, re.IGNORECASE)
                            for match in matches:
                                # Get line number
                                line_num = content[:match.start()].count('\n') + 1
                                line_content = lines[line_num - 1] if line_num <= len(lines) else ''
                                
                                if filepath not in results:
                                    results[filepath] = []
                                results[filepath].append({
                                    'pattern': pattern,
                                    'line': line_num,
                                    'content': line_content.strip(),
                                    'match': match.group()
                                })
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    return results

def main():
    root_dir = Path(__file__).parent.parent
    print(f"Searching for cosine similarity patterns in: {root_dir}")
    print("=" * 80)
    
    results = search_for_cosine_patterns(root_dir)
    
    if not results:
        print("No cosine similarity patterns found.")
        return
    
    for filepath, matches in sorted(results.items()):
        print(f"\n📄 {filepath}")
        print("-" * 80)
        for match in matches:
            print(f"  Line {match['line']:4d} | Pattern: {match['pattern']:30s} | {match['content'][:60]}")

if __name__ == '__main__':
    main()

