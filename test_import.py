#!/usr/bin/env python3
"""
Test script to verify MCP modules can be imported
"""

try:
    print("Testing imports...")
    
    # Test basic imports
    from database import DatabaseManager
    print("✅ DatabaseManager imported successfully")
    
    from tools import process_content_for_platform, PLATFORM_LIMITS
    print("✅ Tools imported successfully")
    
    from simple_mcp import simple_mcp_server
    print("✅ Simple MCP server imported successfully")
    
    from simple_mcp_api import simple_mcp_router
    print("✅ Simple MCP API router imported successfully")
    
    print("\n🎉 All imports successful! MCP should work.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
