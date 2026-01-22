#!/usr/bin/env python3
"""
Verify that the generate-content endpoint is properly registered
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from main import app
    
    # Get all routes
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            for method in route.methods:
                routes.append(f"{method} {route.path}")
    
    # Check for generate-content endpoint
    generate_content_routes = [r for r in routes if 'generate-content' in r]
    
    print("=" * 60)
    print("Route Verification")
    print("=" * 60)
    print(f"\nTotal routes: {len(routes)}")
    print(f"\nRoutes containing 'generate-content':")
    if generate_content_routes:
        for route in generate_content_routes:
            print(f"  ✅ {route}")
    else:
        print("  ❌ No generate-content routes found!")
    
    print(f"\nAll routes containing 'campaigns':")
    campaign_routes = [r for r in routes if 'campaigns' in r]
    for route in sorted(campaign_routes):
        print(f"  {route}")
    
    # Check if brand_personalities_router is loaded
    print(f"\nRouter check:")
    try:
        from app.routes.brand_personalities import brand_personalities_router
        print(f"  ✅ brand_personalities_router imported successfully")
        print(f"  ✅ Router has {len(brand_personalities_router.routes)} routes")
    except Exception as e:
        print(f"  ❌ Failed to import brand_personalities_router: {e}")
    
    if not generate_content_routes:
        print("\n" + "=" * 60)
        print("⚠️  WARNING: generate-content endpoint not found!")
        print("=" * 60)
        print("\nPossible causes:")
        print("  1. Backend server needs to be restarted")
        print("  2. Router import failed (check logs)")
        print("  3. Route definition has syntax error")
        sys.exit(1)
    else:
        print("\n" + "=" * 60)
        print("✅ generate-content endpoint is registered")
        print("=" * 60)
        sys.exit(0)
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

