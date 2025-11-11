#!/usr/bin/env python3
"""
Test script to compare CrewAI vs Manual content generation
Run: python3 test_crewai_vs_manual.py
"""

import requests
import json
import sys
from typing import Dict, Any

BASE_URL = "https://themachine.vernalcontentum.com"
# For local testing, use: BASE_URL = "http://127.0.0.1:8000"

TEST_TEXT = """Artificial intelligence is transforming the way we work and think about technology. 
Machine learning algorithms are becoming more sophisticated, enabling computers to process information 
in ways that were previously impossible. This revolution is affecting industries from healthcare to finance, 
creating new opportunities and challenges."""

def test_manual_orchestration() -> Dict[str, Any]:
    """Test manual step-by-step orchestration"""
    print("📋 Test 1: Manual Orchestration")
    print("=" * 50)
    print("Endpoint: POST /mcp/generate-content")
    print()
    
    try:
        response = requests.post(
            f"{BASE_URL}/mcp/generate-content",
            json={
                "text": TEST_TEXT,
                "platform": "linkedin",
                "week": 1
            },
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        print("✅ Success!")
        print(json.dumps(result, indent=2))
        return result
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": str(e)}

def test_crewai_orchestration() -> Dict[str, Any]:
    """Test CrewAI agent-to-agent orchestration"""
    print("\n📋 Test 2: CrewAI Orchestration")
    print("=" * 50)
    print("Endpoint: POST /mcp/tools/execute")
    print("Tool: crewai_content_generation")
    print()
    
    try:
        response = requests.post(
            f"{BASE_URL}/mcp/tools/execute",
            json={
                "tool_name": "crewai_content_generation",
                "input_data": {
                    "text": TEST_TEXT,
                    "platform": "linkedin",
                    "week": 1,
                    "use_qc": True
                }
            },
            timeout=300  # CrewAI may take longer
        )
        response.raise_for_status()
        result = response.json()
        print("✅ Success!")
        print(json.dumps(result, indent=2))
        return result
    except Exception as e:
        print(f"❌ Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"Response: {e.response.text}")
            except:
                pass
        return {"error": str(e)}

def list_available_tools() -> list:
    """List all available MCP tools"""
    print("\n📋 Test 3: List Available Tools")
    print("=" * 50)
    print("Endpoint: GET /mcp/tools")
    print()
    
    try:
        response = requests.get(f"{BASE_URL}/mcp/tools", timeout=10)
        response.raise_for_status()
        tools = response.json()
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool.get('name', 'unknown')}: {tool.get('description', 'No description')[:60]}...")
        return tools
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def compare_results(manual_result: Dict, crewai_result: Dict):
    """Compare the results from both methods"""
    print("\n📊 Comparison")
    print("=" * 50)
    
    manual_success = manual_result.get("success", False)
    crewai_success = crewai_result.get("success", False)
    
    print(f"Manual Orchestration: {'✅ Success' if manual_success else '❌ Failed'}")
    print(f"CrewAI Orchestration: {'✅ Success' if crewai_success else '❌ Failed'}")
    
    if manual_success and crewai_success:
        print("\nBoth methods succeeded! Compare the outputs above to see differences.")
        print("\nKey differences to look for:")
        print("  - CrewAI: Agents can see previous agent outputs (context awareness)")
        print("  - CrewAI: Better error recovery and agent collaboration")
        print("  - Manual: Faster, simpler, more predictable")
    elif not crewai_success:
        print("\n⚠️  CrewAI test failed. Check if:")
        print("  - CrewAI is installed: pip install crewai")
        print("  - Backend logs for errors")
        print("  - Tool is registered: Check /mcp/tools endpoint")

if __name__ == "__main__":
    print("🧪 Testing Content Generation: CrewAI vs Manual")
    print("=" * 50)
    print()
    
    # Test 1: Manual
    manual_result = test_manual_orchestration()
    
    # Test 2: CrewAI
    crewai_result = test_crewai_orchestration()
    
    # Test 3: List tools
    tools = list_available_tools()
    
    # Compare
    compare_results(manual_result, crewai_result)
    
    print("\n✅ Testing Complete!")
    print("\nTo test manually with curl:")
    print("  Manual: curl -X POST https://themachine.vernalcontentum.com/mcp/generate-content -H 'Content-Type: application/json' -d '{\"text\":\"...\",\"platform\":\"linkedin\"}'")
    print("  CrewAI: curl -X POST https://themachine.vernalcontentum.com/mcp/tools/execute -H 'Content-Type: application/json' -d '{\"tool_name\":\"crewai_content_generation\",\"input_data\":{\"text\":\"...\",\"platform\":\"linkedin\"}}'")

