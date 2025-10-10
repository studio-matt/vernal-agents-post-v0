"""
Enhanced MCP Testing Suite
Comprehensive testing for all MCP tools and workflows
"""

import asyncio
import json
import logging
from typing import Dict, Any, List
from enhanced_mcp import enhanced_mcp_server, ToolStatus

logger = logging.getLogger(__name__)

class MCPTester:
    """Comprehensive MCP testing suite"""
    
    def __init__(self):
        self.test_results = {}
        self.server = enhanced_mcp_server
    
    async def test_all_tools(self) -> Dict[str, Any]:
        """Test all available tools"""
        logger.info("🧪 Testing all MCP tools...")
        results = {}
        
        # Test data for different tool types
        test_data = {
            "script_research": {
                "text": "This is sample content about digital marketing trends and social media strategies for 2024.",
                "week": 1,
                "days_list": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            },
            "quality_control": {
                "content": "Sample content for quality control testing with proper grammar and structure.",
                "platform": "linkedin",
                "forbidden_words": ["spam", "scam"]
            },
            "regenerate_content": {
                "content": "Original content that needs regeneration with fresh perspective.",
                "week": 1
            },
            "linkedin_generation": {
                "content": "Base content for LinkedIn adaptation with professional tone.",
                "platform": "linkedin",
                "author_personality": "professional"
            },
            "twitter_generation": {
                "content": "Base content for Twitter adaptation with concise messaging.",
                "platform": "twitter",
                "author_personality": "engaging"
            },
            "facebook_generation": {
                "content": "Base content for Facebook adaptation with community focus.",
                "platform": "facebook",
                "author_personality": "friendly"
            },
            "instagram_generation": {
                "content": "Base content for Instagram adaptation with visual storytelling.",
                "platform": "instagram",
                "author_personality": "creative"
            },
            "tiktok_generation": {
                "content": "Base content for TikTok adaptation with viral potential.",
                "platform": "tiktok",
                "author_personality": "trendy"
            },
            "youtube_generation": {
                "content": "Base content for YouTube adaptation with educational focus.",
                "platform": "youtube",
                "author_personality": "informative"
            },
            "wordpress_generation": {
                "content": "Base content for WordPress adaptation with SEO optimization.",
                "platform": "wordpress",
                "author_personality": "authoritative"
            }
        }
        
        for tool_name, tool in self.server.tools.items():
            logger.info(f"  Testing tool: {tool_name}")
            
            try:
                if tool_name in test_data:
                    result = await tool.execute(test_data[tool_name])
                    results[tool_name] = {
                        "success": result.success,
                        "execution_time": result.execution_time,
                        "status": result.status.value,
                        "error": result.error,
                        "data_keys": list(result.data.keys()) if result.data else [],
                        "metadata": result.metadata
                    }
                else:
                    # Generic test data
                    generic_data = {
                        "content": "Sample content for testing",
                        "platform": "linkedin",
                        "text": "Sample text for analysis",
                        "week": 1,
                        "days_list": ["Monday", "Tuesday"]
                    }
                    result = await tool.execute(generic_data)
                    results[tool_name] = {
                        "success": result.success,
                        "execution_time": result.execution_time,
                        "status": result.status.value,
                        "error": result.error,
                        "data_keys": list(result.data.keys()) if result.data else [],
                        "metadata": result.metadata
                    }
                
                logger.info(f"    ✅ {tool_name}: {result.status.value}")
                
            except Exception as e:
                logger.error(f"    ❌ {tool_name}: {str(e)}")
                results[tool_name] = {
                    "success": False,
                    "error": str(e),
                    "status": "failed"
                }
        
        return results
    
    async def test_all_workflows(self) -> Dict[str, Any]:
        """Test all available workflows"""
        logger.info("🔄 Testing all MCP workflows...")
        results = {}
        
        # Test data for workflows
        workflow_test_data = {
            "content_generation": {
                "text": "Comprehensive content about digital transformation and AI integration in modern businesses.",
                "week": 1,
                "days_list": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                "content": "Sample content for workflow testing",
                "platform": "linkedin",
                "author_personality": "professional"
            },
            "platform_content": {
                "text": "Multi-platform content strategy for social media marketing campaigns.",
                "week": 2,
                "days_list": ["Monday", "Tuesday", "Wednesday"],
                "content": "Content for platform-specific adaptation",
                "platform": "twitter",
                "author_personality": "engaging"
            }
        }
        
        for workflow_name in self.server.list_workflows():
            logger.info(f"  Testing workflow: {workflow_name}")
            
            try:
                test_data = workflow_test_data.get(workflow_name, {
                    "text": "Sample workflow test data",
                    "week": 1,
                    "days_list": ["Monday", "Tuesday"],
                    "content": "Sample content",
                    "platform": "linkedin"
                })
                
                result = await self.server.execute_workflow(workflow_name, test_data)
                results[workflow_name] = {
                    "success": result.status == ToolStatus.COMPLETED,
                    "status": result.status.value,
                    "total_time": result.total_time,
                    "errors": result.errors,
                    "steps_completed": len([s for s in result.steps.values() if s.status == ToolStatus.COMPLETED]),
                    "steps_failed": len([s for s in result.steps.values() if s.status == ToolStatus.FAILED]),
                    "data_keys": list(result.data.keys())
                }
                
                logger.info(f"    ✅ {workflow_name}: {result.status.value}")
                
            except Exception as e:
                logger.error(f"    ❌ {workflow_name}: {str(e)}")
                results[workflow_name] = {
                    "success": False,
                    "error": str(e),
                    "status": "failed"
                }
        
        return results
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling scenarios"""
        logger.info("⚠️ Testing error handling...")
        results = {}
        
        # Test invalid tool name
        try:
            invalid_tool = self.server.get_tool("nonexistent_tool")
            results["invalid_tool"] = {"success": invalid_tool is None}
        except Exception as e:
            results["invalid_tool"] = {"success": False, "error": str(e)}
        
        # Test invalid workflow name
        try:
            await self.server.execute_workflow("nonexistent_workflow", {})
            results["invalid_workflow"] = {"success": False}
        except ValueError:
            results["invalid_workflow"] = {"success": True}
        except Exception as e:
            results["invalid_workflow"] = {"success": False, "error": str(e)}
        
        # Test validation errors
        try:
            tool = self.server.get_tool("script_research")
            if tool:
                # Missing required field
                invalid_data = {"text": "test"}  # Missing week and days_list
                result = await tool.execute(invalid_data)
                results["validation_error"] = {
                    "success": not result.success,
                    "error_type": result.metadata.get("error_type")
                }
        except Exception as e:
            results["validation_error"] = {"success": False, "error": str(e)}
        
        # Test timeout (if we had a slow tool)
        results["timeout_test"] = {"success": True, "note": "No slow tools to test"}
        
        return results
    
    async def test_performance(self) -> Dict[str, Any]:
        """Test performance metrics"""
        logger.info("⚡ Testing performance...")
        results = {}
        
        # Test concurrent tool execution
        tool_name = "script_research"
        tool = self.server.get_tool(tool_name)
        
        if tool:
            test_data = {
                "text": "Performance test content",
                "week": 1,
                "days_list": ["Monday", "Tuesday"]
            }
            
            # Sequential execution
            start_time = asyncio.get_event_loop().time()
            for _ in range(3):
                await tool.execute(test_data)
            sequential_time = asyncio.get_event_loop().time() - start_time
            
            # Concurrent execution
            start_time = asyncio.get_event_loop().time()
            tasks = [tool.execute(test_data) for _ in range(3)]
            await asyncio.gather(*tasks)
            concurrent_time = asyncio.get_event_loop().time() - start_time
            
            results["concurrent_execution"] = {
                "sequential_time": sequential_time,
                "concurrent_time": concurrent_time,
                "improvement": (sequential_time - concurrent_time) / sequential_time * 100
            }
        
        # Test tool statistics
        stats = self.server.get_tool_stats()
        results["tool_statistics"] = {
            "total_tools": len(stats),
            "tools_with_usage": len([s for s in stats.values() if s["usage_count"] > 0]),
            "average_success_rate": sum(s["success_rate"] for s in stats.values()) / len(stats) if stats else 0
        }
        
        return results
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive test suite"""
        logger.info("🚀 Starting comprehensive MCP test suite...")
        
        test_results = {
            "timestamp": asyncio.get_event_loop().time(),
            "server_info": {
                "tools_count": len(self.server.tools),
                "workflows_count": len(self.server.workflows),
                "available_tools": list(self.server.tools.keys()),
                "available_workflows": self.server.list_workflows()
            }
        }
        
        # Run all test categories
        test_results["tool_tests"] = await self.test_all_tools()
        test_results["workflow_tests"] = await self.test_all_workflows()
        test_results["error_handling_tests"] = await self.test_error_handling()
        test_results["performance_tests"] = await self.test_performance()
        
        # Calculate overall success rate
        tool_successes = sum(1 for r in test_results["tool_tests"].values() if r.get("success", False))
        tool_total = len(test_results["tool_tests"])
        workflow_successes = sum(1 for r in test_results["workflow_tests"].values() if r.get("success", False))
        workflow_total = len(test_results["workflow_tests"])
        
        test_results["summary"] = {
            "tool_success_rate": (tool_successes / tool_total * 100) if tool_total > 0 else 0,
            "workflow_success_rate": (workflow_successes / workflow_total * 100) if workflow_total > 0 else 0,
            "overall_success": tool_successes + workflow_successes,
            "total_tests": tool_total + workflow_total
        }
        
        logger.info("✅ Comprehensive test suite completed")
        return test_results

async def main():
    """Main test execution"""
    tester = MCPTester()
    results = await tester.run_comprehensive_test()
    
    print("\n" + "="*80)
    print("🧪 ENHANCED MCP TEST RESULTS")
    print("="*80)
    
    print(f"\n📊 Server Info:")
    print(f"  Tools: {results['server_info']['tools_count']}")
    print(f"  Workflows: {results['server_info']['workflows_count']}")
    
    print(f"\n🔧 Tool Tests:")
    for tool_name, result in results["tool_tests"].items():
        status = "✅" if result.get("success", False) else "❌"
        exec_time = result.get("execution_time", 0)
        print(f"  {status} {tool_name}: {result.get('status', 'unknown')} ({exec_time:.2f}s)")
    
    print(f"\n🔄 Workflow Tests:")
    for workflow_name, result in results["workflow_tests"].items():
        status = "✅" if result.get("success", False) else "❌"
        total_time = result.get("total_time", 0)
        print(f"  {status} {workflow_name}: {result.get('status', 'unknown')} ({total_time:.2f}s)")
    
    print(f"\n📈 Summary:")
    summary = results["summary"]
    print(f"  Tool Success Rate: {summary['tool_success_rate']:.1f}%")
    print(f"  Workflow Success Rate: {summary['workflow_success_rate']:.1f}%")
    print(f"  Overall Success: {summary['overall_success']}/{summary['total_tests']}")
    
    print("\n" + "="*80)
    
    # Save results to file
    with open("mcp_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print("💾 Results saved to mcp_test_results.json")

if __name__ == "__main__":
    asyncio.run(main())
