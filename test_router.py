#!/usr/bin/env python3
"""
Test script to verify router files work correctly
"""

import sys
import traceback

def test_router_file(filename, router_name):
    """Test a single router file"""
    print(f"Testing {filename}...")
    try:
        # Import the module
        module = __import__(filename.replace('.py', ''))
        
        # Check if router exists
        if hasattr(module, router_name):
            router = getattr(module, router_name)
            print(f"✅ {filename} - {router_name} found")
            
            # Check if router has routes
            if hasattr(router, 'routes'):
                print(f"   Routes: {len(router.routes)}")
                for route in router.routes:
                    if hasattr(route, 'path'):
                        print(f"   - {route.path}")
            else:
                print(f"   No routes attribute found")
            
            return True
        else:
            print(f"❌ {filename} - {router_name} not found")
            return False
            
    except Exception as e:
        print(f"❌ {filename} - Error: {e}")
        traceback.print_exc()
        return False

def main():
    """Test all router files"""
    print("Testing router files...")
    
    # Test simple_mcp_api
    test_router_file("simple_mcp_api.py", "simple_mcp_router")
    
    # Test debug_import
    test_router_file("debug_import.py", "router")
    
    print("Router testing complete")

if __name__ == "__main__":
    main()
