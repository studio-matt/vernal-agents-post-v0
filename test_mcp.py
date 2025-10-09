"""
Test script for MCP tools and workflows
"""

import asyncio
import json
from mcp_server import mcp_server
from mcp_workflows import workflow_manager

async def test_mcp_tools():
    """Test individual MCP tools"""
    print("🧪 Testing MCP Tools...")
    
    # Test script research tool
    print("\n1. Testing Script Research Tool:")
    research_result = await mcp_server.get_tool("script_research").execute({
        "text": "This is a sample text about artificial intelligence and machine learning. It covers various topics including neural networks, deep learning, and natural language processing.",
        "week": 1,
        "days_list": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    })
    print(f"   Success: {research_result.success}")
    if research_result.success:
        print(f"   Data: {json.dumps(research_result.data, indent=2)}")
    else:
        print(f"   Error: {research_result.error}")
    
    # Test platform generation tool
    print("\n2. Testing LinkedIn Generation Tool:")
    linkedin_result = await mcp_server.get_tool("linkedin_generation").execute({
        "content": "AI is transforming the way we work and think about technology.",
        "platform": "linkedin",
        "author_personality": "professional"
    })
    print(f"   Success: {linkedin_result.success}")
    if linkedin_result.success:
        print(f"   Data: {json.dumps(linkedin_result.data, indent=2)}")
    else:
        print(f"   Error: {linkedin_result.error}")
    
    # Test quality control tool
    print("\n3. Testing Quality Control Tool:")
    qc_result = await mcp_server.get_tool("quality_control").execute({
        "content": "This is a test content for quality control review.",
        "platform": "linkedin",
        "forbidden_words": ["bad", "terrible"]
    })
    print(f"   Success: {qc_result.success}")
    if qc_result.success:
        print(f"   Data: {json.dumps(qc_result.data, indent=2)}")
    else:
        print(f"   Error: {qc_result.error}")

async def test_mcp_workflows():
    """Test MCP workflows"""
    print("\n🔄 Testing MCP Workflows...")
    
    # Test content generation workflow
    print("\n1. Testing Content Generation Workflow:")
    workflow_result = await workflow_manager.execute_workflow("content_generation", {
        "text": "Sample text about digital transformation in business. This covers topics like automation, AI integration, and process optimization.",
        "week": 1,
        "platform": "linkedin",
        "campaign_id": "test-123",
        "author_personality": "professional"
    })
    print(f"   Success: {workflow_result.success}")
    if workflow_result.success:
        print(f"   Steps Completed: {workflow_result.steps_completed}")
        print(f"   Data Keys: {list(workflow_result.data.keys()) if workflow_result.data else 'None'}")
    else:
        print(f"   Error: {workflow_result.error}")
    
    # Test content regeneration workflow
    print("\n2. Testing Content Regeneration Workflow:")
    regen_result = await workflow_manager.execute_workflow("content_regeneration", {
        "type": "weekly",
        "content": "Original content about innovation and technology trends.",
        "week": 1,
        "platform": "twitter"
    })
    print(f"   Success: {regen_result.success}")
    if regen_result.success:
        print(f"   Steps Completed: {regen_result.steps_completed}")
        print(f"   Data Keys: {list(regen_result.data.keys()) if regen_result.data else 'None'}")
    else:
        print(f"   Error: {regen_result.error}")

async def test_mcp_server_info():
    """Test MCP server information"""
    print("\n📊 MCP Server Information:")
    print(f"   Server Name: {mcp_server.name}")
    print(f"   Tools Count: {len(mcp_server.tools)}")
    print(f"   Available Tools: {list(mcp_server.tools.keys())}")
    
    print(f"\n   Workflows Count: {len(workflow_manager.workflows)}")
    print(f"   Available Workflows: {workflow_manager.list_workflows()}")

async def main():
    """Main test function"""
    print("🚀 Starting MCP Tests...")
    
    try:
        await test_mcp_server_info()
        await test_mcp_tools()
        await test_mcp_workflows()
        
        print("\n✅ All MCP tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
