#!/usr/bin/env python3
"""
Test script to check if all imports work correctly
"""

import sys
import traceback
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_import(module_name, import_statement):
    """Test a single import"""
    try:
        exec(import_statement)
        logger.info(f"✅ {module_name} imported successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to import {module_name}: {e}")
        traceback.print_exc()
        return False

def main():
    """Test all critical imports"""
    logger.info("Testing all critical imports...")
    
    # Test basic imports
    test_import("os", "import os")
    test_import("fastapi", "from fastapi import FastAPI")
    test_import("database", "from database import db_manager")
    test_import("agents", "from agents import script_research_agent")
    test_import("tools", "from tools import process_content_for_platform")
    
    # Test router imports
    test_import("simple_mcp_api", "from simple_mcp_api import simple_mcp_router")
    test_import("debug_import", "from debug_import import router")
    
    # Test MCP imports
    test_import("simple_mcp", "from simple_mcp import simple_mcp_server")
    
    logger.info("Import testing complete")

if __name__ == "__main__":
    main()
