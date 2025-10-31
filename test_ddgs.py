#!/usr/bin/env python3
"""
Quick test script to see what ddgs actually returns
"""
from ddgs import DDGS

with DDGS() as ddgs:
    print("Testing DuckDuckGo search...")
    results = ddgs.text("python programming", max_results=3)
    
    print("\n=== First result ===")
    first = next(results, None)
    if first:
        print(f"Type: {type(first)}")
        print(f"Content: {first}")
        if isinstance(first, dict):
            print(f"Keys: {list(first.keys())}")
    
    # Try to get a few more
    print("\n=== Processing results ===")
    count = 0
    with DDGS() as ddgs2:
        for result in ddgs2.text("python programming", max_results=5):
            count += 1
            print(f"\nResult {count}:")
            print(f"  Type: {type(result)}")
            if isinstance(result, dict):
                print(f"  Keys: {list(result.keys())}")
                for key in ['href', 'url', 'link', 'body']:
                    if key in result:
                        print(f"  {key}: {result[key]}")
            else:
                print(f"  Value: {result}")
            if count >= 3:
                break

