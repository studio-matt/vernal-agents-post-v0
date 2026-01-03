#!/usr/bin/env python3
"""
Fix script for cosine similarity inversion bug.

This script helps locate and fix the pairwise z-scoring issue that causes
cosine similarity to always return -1.0.

Usage:
1. Run this script to search for cosine similarity calculations
2. Review the findings
3. Apply the fix to the identified code
"""

import re
import sys
from pathlib import Path

def find_cosine_calculations(root_dir):
    """Find all potential cosine similarity calculation locations."""
    patterns = [
        (r'cosine.*similarity|similarity.*cosine', 'cosine similarity'),
        (r'from scipy.*spatial|from sklearn.*metrics', 'scipy/sklearn import'),
        (r'pairwise.*z.*score|z.*score.*pairwise', 'pairwise z-scoring'),
        (r'standardize.*two|normalize.*two', 'pairwise normalization'),
        (r'BH.*LVT|LVT.*BH', 'BH-LVT reference'),
        (r'punctuation.*cosine|cosine.*punctuation', 'punctuation cosine'),
        (r'weighted.*cosine|cosine.*weighted', 'weighted cosine'),
    ]
    
    results = []
    
    for root, dirs, files in Path(root_dir).rwalk():
        # Skip common directories
        dirs[:] = [d for d in dirs if d.name not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv']]
        
        for file in files:
            if file.suffix == '.py':
                filepath = root / file
                try:
                    content = filepath.read_text(encoding='utf-8')
                    lines = content.split('\n')
                    
                    for pattern, description in patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            line_content = lines[line_num - 1] if line_num <= len(lines) else ''
                            
                            results.append({
                                'file': str(filepath.relative_to(root_dir)),
                                'line': line_num,
                                'pattern': description,
                                'content': line_content.strip(),
                                'match': match.group()
                            })
                except Exception as e:
                    print(f"Error reading {filepath}: {e}", file=sys.stderr)
    
    return results

def print_fix_guide():
    """Print the fix guide."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    COSINE SIMILARITY FIX GUIDE                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

PROBLEM:
--------
Cosine similarity returning exactly -1.0 due to pairwise z-scoring artifact.
When z-scoring is applied using only the two texts being compared, vectors
become exact opposites → cosine = -1.0 deterministically.

SYMPTOMS:
---------
- BH-LVT weighted cosine = -1.0 (exact)
- Punctuation cosine = -1.0 (exact)
- Function-word similarity works correctly (uses different method)

ROOT CAUSE:
-----------
Pairwise z-scoring: Standardizing using only the two texts being compared.
With only two samples, per-feature z-scores become +1 vs -1, making vectors
antipodes → cosine becomes -1 regardless of actual relationship.

FIX:
----
Replace pairwise z-scoring with baseline normalization using global LIWC
baselines that are already loaded in the system.

BEFORE (WRONG):
---------------
```python
# Pairwise z-scoring - causes -1.0 cosine similarity
def compute_similarity(text1_features, text2_features):
    # Standardize using only these two texts
    mean = (text1_features + text2_features) / 2
    std = np.std([text1_features, text2_features], axis=0)
    z1 = (text1_features - mean) / std
    z2 = (text2_features - mean) / std
    # z1 and z2 are now opposites → cosine = -1.0
    return cosine_similarity(z1, z2)
```

AFTER (CORRECT):
----------------
```python
# Use baseline normalization across multiple texts
from author_related.asset_loader import AssetLoader

def compute_similarity(text1_features, text2_features, category_names):
    loader = AssetLoader()
    baselines = loader.load_liwc_baselines()
    
    # Standardize each feature using global baseline, not pairwise
    z1 = []
    z2 = []
    for category in category_names:
        baseline = baselines.get(category, {"mean": 0.0, "stdev": 1.0})
        mean = baseline.get("mean", 0.0)
        stdev = baseline.get("stdev", 1.0) or 1.0
        
        # Z-score each feature independently using global baseline
        z1_val = (text1_features[category] - mean) / stdev
        z2_val = (text2_features[category] - mean) / stdev
        
        z1.append(z1_val)
        z2.append(z2_val)
    
    # Now cosine similarity reflects actual relationship
    return cosine_similarity(z1, z2)
```

ALTERNATIVE (if comparing profiles):
-----------------------------------
```python
# If comparing two AuthorProfile objects, use their existing z-scores
def compute_profile_similarity(profile1, profile2, category_names):
    z1 = [profile1.liwc_profile.categories[cat].z for cat in category_names]
    z2 = [profile2.liwc_profile.categories[cat].z for cat in category_names]
    return cosine_similarity(z1, z2)
```

VALIDATION TEST:
----------------
```python
def test_cosine_similarity():
    # Test 1: Identical texts should return 1.0
    text1 = "This is a test."
    text2 = "This is a test."
    similarity = compute_similarity(text1, text2, categories)
    assert abs(similarity - 1.0) < 0.01, f"Expected ~1.0, got {similarity}"
    
    # Test 2: Different texts should not be exactly -1.0
    text3 = "This is completely different content."
    similarity = compute_similarity(text1, text3, categories)
    assert similarity > -1.0, f"Expected > -1.0, got {similarity}"
    
    # Test 3: Similar texts should have positive similarity
    text4 = "This is a similar test."
    similarity = compute_similarity(text1, text4, categories)
    assert similarity > 0, f"Expected > 0, got {similarity}"
```

WHERE TO LOOK:
--------------
1. Functions that compare two profiles
2. Functions that compare profile vs generated text
3. Analysis/comparison endpoints in main.py
4. Any code that computes "BH-LVT" or "punctuation" similarity
5. Code that uses scipy.spatial.distance.cosine or sklearn.metrics.pairwise.cosine_similarity

CHECKLIST:
----------
□ Locate the cosine similarity calculation code
□ Identify where pairwise z-scoring is applied
□ Replace with baseline normalization using AssetLoader
□ Verify similarity metric is not inverted (distance vs similarity)
□ Add validation test for (A, A) case
□ Test with different text pairs to verify fix
□ Check delta direction in rebalancing step (if applicable)

""")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--guide':
        print_fix_guide()
        return
    
    root_dir = Path(__file__).parent.parent
    print(f"Searching for cosine similarity calculations in: {root_dir}")
    print("=" * 80)
    
    results = find_cosine_calculations(root_dir)
    
    if not results:
        print("No cosine similarity patterns found.")
        print("\nRun with --guide flag to see the fix guide:")
        print("  python3 scripts/fix_cosine_similarity.py --guide")
        return
    
    # Group by file
    by_file = {}
    for result in results:
        file = result['file']
        if file not in by_file:
            by_file[file] = []
        by_file[file].append(result)
    
    for file, matches in sorted(by_file.items()):
        print(f"\n📄 {file}")
        print("-" * 80)
        for match in sorted(matches, key=lambda x: x['line']):
            print(f"  Line {match['line']:4d} | {match['pattern']:30s} | {match['content'][:60]}")
    
    print("\n" + "=" * 80)
    print(f"Found {len(results)} potential matches across {len(by_file)} files")
    print("\nRun with --guide flag to see the fix guide:")
    print("  python3 scripts/fix_cosine_similarity.py --guide")

if __name__ == '__main__':
    main()

