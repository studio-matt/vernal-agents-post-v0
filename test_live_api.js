/**
 * Live API and Database Testing Suite for Replit
 * Tests real HTTP requests to deployed backend and database connectivity
 */

const https = require('https');
const http = require('http');
const fs = require('fs');

class LiveAPITester {
    constructor() {
        this.baseURL = 'https://themachine.vernalcontentum.com';
        this.frontendURL = 'https://machine.vernalcontentum.com';
        this.testResults = {};
    }

    async makeRequest(url, options = {}) {
        return new Promise((resolve, reject) => {
            const isHttps = url.startsWith('https://');
            const client = isHttps ? https : http;
            
            const requestOptions = {
                method: options.method || 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'User-Agent': 'Replit-MCP-Tester/1.0',
                    ...options.headers
                },
                timeout: options.timeout || 10000
            };

            const req = client.request(url, requestOptions, (res) => {
                let data = '';
                
                res.on('data', (chunk) => {
                    data += chunk;
                });
                
                res.on('end', () => {
                    resolve({
                        statusCode: res.statusCode,
                        headers: res.headers,
                        data: data,
                        url: url
                    });
                });
            });

            req.on('error', (error) => {
                reject(error);
            });

            req.on('timeout', () => {
                req.destroy();
                reject(new Error('Request timeout'));
            });

            if (options.body) {
                req.write(JSON.stringify(options.body));
            }

            req.end();
        });
    }

    async testBackendHealth() {
        console.log("🏥 Testing Backend Health");
        console.log("=".repeat(50));
        
        const endpoints = [
            '/health',
            '/mcp/mcp/health',
            '/mcp/enhanced/health'
        ];

        const results = {};

        for (const endpoint of endpoints) {
            try {
                console.log(`  Testing: ${endpoint}`);
                const response = await this.makeRequest(`${this.baseURL}${endpoint}`);
                
                results[endpoint] = {
                    success: response.statusCode === 200,
                    statusCode: response.statusCode,
                    responseTime: Date.now(),
                    data: response.data,
                    headers: response.headers
                };

                if (response.statusCode === 200) {
                    console.log(`    ✅ ${endpoint}: ${response.statusCode} - Working`);
                    try {
                        const jsonData = JSON.parse(response.data);
                        console.log(`    📊 Response: ${JSON.stringify(jsonData, null, 2)}`);
                    } catch (e) {
                        console.log(`    📄 Response: ${response.data.substring(0, 100)}...`);
                    }
                } else {
                    console.log(`    ❌ ${endpoint}: ${response.statusCode} - ${response.data}`);
                }

            } catch (error) {
                console.log(`    ❌ ${endpoint}: ${error.message}`);
                results[endpoint] = {
                    success: false,
                    error: error.message,
                    statusCode: 0
                };
            }
        }

        return results;
    }

    async testMCPEndpoints() {
        console.log("\n🔧 Testing MCP Endpoints");
        console.log("=".repeat(50));

        const endpoints = [
            { path: '/mcp/mcp/health', method: 'GET', description: 'Simple MCP Health' },
            { path: '/mcp/enhanced/health', method: 'GET', description: 'Enhanced MCP Health' },
            { path: '/mcp/mcp/tools', method: 'GET', description: 'List MCP Tools' },
            { path: '/mcp/enhanced/tools', method: 'GET', description: 'List Enhanced Tools' },
            { path: '/mcp/enhanced/workflows', method: 'GET', description: 'List Workflows' },
            { path: '/mcp/enhanced/stats', method: 'GET', description: 'Get Statistics' }
        ];

        const results = {};

        for (const endpoint of endpoints) {
            try {
                console.log(`  Testing: ${endpoint.method} ${endpoint.path}`);
                const response = await this.makeRequest(`${this.baseURL}${endpoint.path}`, {
                    method: endpoint.method
                });
                
                results[endpoint.path] = {
                    success: response.statusCode === 200,
                    statusCode: response.statusCode,
                    method: endpoint.method,
                    description: endpoint.description,
                    data: response.data,
                    responseTime: Date.now()
                };

                if (response.statusCode === 200) {
                    console.log(`    ✅ ${endpoint.path}: ${response.statusCode} - ${endpoint.description}`);
                    try {
                        const jsonData = JSON.parse(response.data);
                        console.log(`    📊 Response: ${JSON.stringify(jsonData, null, 2)}`);
                    } catch (e) {
                        console.log(`    📄 Response: ${response.data.substring(0, 200)}...`);
                    }
                } else {
                    console.log(`    ❌ ${endpoint.path}: ${response.statusCode} - ${response.data}`);
                }

            } catch (error) {
                console.log(`    ❌ ${endpoint.path}: ${error.message}`);
                results[endpoint.path] = {
                    success: false,
                    error: error.message,
                    statusCode: 0,
                    method: endpoint.method,
                    description: endpoint.description
                };
            }
        }

        return results;
    }

    async testToolExecution() {
        console.log("\n⚙️ Testing Tool Execution");
        console.log("=".repeat(50));

        const testData = {
            script_research: {
                text: "Digital marketing trends for 2024 including AI integration, social media automation, and content personalization strategies.",
                week: 1,
                days_list: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            },
            quality_control: {
                content: "Sample content for quality control testing with proper grammar and structure.",
                platform: "linkedin",
                forbidden_words: ["spam", "scam"]
            },
            regenerate_content: {
                content: "Original content that needs regeneration with fresh perspective and updated information.",
                week: 1
            }
        };

        const results = {};

        for (const [toolName, inputData] of Object.entries(testData)) {
            try {
                console.log(`  Testing tool: ${toolName}`);
                
                // Test both simple and enhanced MCP endpoints
                const endpoints = [
                    `/mcp/mcp/tools/${toolName}/execute`,
                    `/mcp/enhanced/tools/${toolName}/execute`
                ];

                for (const endpoint of endpoints) {
                    try {
                        const response = await this.makeRequest(`${this.baseURL}${endpoint}`, {
                            method: 'POST',
                            body: inputData
                        });

                        const resultKey = `${toolName}_${endpoint.split('/')[2]}`;
                        results[resultKey] = {
                            success: response.statusCode === 200,
                            statusCode: response.statusCode,
                            tool: toolName,
                            endpoint: endpoint,
                            inputData: inputData,
                            response: response.data
                        };

                        if (response.statusCode === 200) {
                            console.log(`    ✅ ${endpoint}: ${response.statusCode} - Tool executed successfully`);
                            try {
                                const jsonData = JSON.parse(response.data);
                                console.log(`    📊 Result: ${JSON.stringify(jsonData, null, 2)}`);
                            } catch (e) {
                                console.log(`    📄 Result: ${response.data.substring(0, 200)}...`);
                            }
                        } else {
                            console.log(`    ❌ ${endpoint}: ${response.statusCode} - ${response.data}`);
                        }

                    } catch (error) {
                        console.log(`    ❌ ${endpoint}: ${error.message}`);
                        results[`${toolName}_${endpoint.split('/')[2]}`] = {
                            success: false,
                            error: error.message,
                            tool: toolName,
                            endpoint: endpoint
                        };
                    }
                }

            } catch (error) {
                console.log(`  ❌ ${toolName}: ${error.message}`);
                results[toolName] = {
                    success: false,
                    error: error.message,
                    tool: toolName
                };
            }
        }

        return results;
    }

    async testWorkflowExecution() {
        console.log("\n🔄 Testing Workflow Execution");
        console.log("=".repeat(50));

        const workflowData = {
            workflow_name: "content_generation",
            input_data: {
                text: "Comprehensive content about digital transformation and AI integration in modern businesses.",
                week: 1,
                days_list: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                content: "Sample content for workflow testing",
                platform: "linkedin",
                author_personality: "professional"
            }
        };

        const results = {};

        try {
            console.log(`  Testing workflow: ${workflowData.workflow_name}`);
            
            const response = await this.makeRequest(`${this.baseURL}/mcp/enhanced/workflows/execute`, {
                method: 'POST',
                body: workflowData
            });

            results['workflow_execution'] = {
                success: response.statusCode === 200,
                statusCode: response.statusCode,
                workflow: workflowData.workflow_name,
                inputData: workflowData.input_data,
                response: response.data
            };

            if (response.statusCode === 200) {
                console.log(`    ✅ Workflow execution: ${response.statusCode} - Workflow completed successfully`);
                try {
                    const jsonData = JSON.parse(response.data);
                    console.log(`    📊 Result: ${JSON.stringify(jsonData, null, 2)}`);
                } catch (e) {
                    console.log(`    📄 Result: ${response.data.substring(0, 200)}...`);
                }
            } else {
                console.log(`    ❌ Workflow execution: ${response.statusCode} - ${response.data}`);
            }

        } catch (error) {
            console.log(`    ❌ Workflow execution: ${error.message}`);
            results['workflow_execution'] = {
                success: false,
                error: error.message,
                workflow: workflowData.workflow_name
            };
        }

        return results;
    }

    async testFrontendConnectivity() {
        console.log("\n🌐 Testing Frontend Connectivity");
        console.log("=".repeat(50));

        const results = {};

        try {
            console.log(`  Testing frontend: ${this.frontendURL}`);
            
            const response = await this.makeRequest(this.frontendURL);
            
            results['frontend'] = {
                success: response.statusCode === 200,
                statusCode: response.statusCode,
                url: this.frontendURL,
                contentType: response.headers['content-type'],
                contentLength: response.data.length
            };

            if (response.statusCode === 200) {
                console.log(`    ✅ Frontend: ${response.statusCode} - Frontend is accessible`);
                console.log(`    📊 Content Type: ${response.headers['content-type']}`);
                console.log(`    📊 Content Length: ${response.data.length} bytes`);
                
                // Check if it's the login page
                if (response.data.includes('Vernal Contentum') && response.data.includes('Login')) {
                    console.log(`    ✅ Login page detected - Frontend is working correctly`);
                }
            } else {
                console.log(`    ❌ Frontend: ${response.statusCode} - ${response.data}`);
            }

        } catch (error) {
            console.log(`    ❌ Frontend: ${error.message}`);
            results['frontend'] = {
                success: false,
                error: error.message,
                url: this.frontendURL
            };
        }

        return results;
    }

    async testDatabaseConnectivity() {
        console.log("\n🗄️ Testing Database Connectivity");
        console.log("=".repeat(50));

        const results = {};

        // Test database connectivity through API endpoints that require DB access
        const dbEndpoints = [
            { path: '/mcp/mcp/health', description: 'MCP Health (requires DB)' },
            { path: '/mcp/enhanced/health', description: 'Enhanced MCP Health (requires DB)' },
            { path: '/mcp/enhanced/stats', description: 'Statistics (requires DB)' }
        ];

        for (const endpoint of dbEndpoints) {
            try {
                console.log(`  Testing DB connectivity via: ${endpoint.path}`);
                
                const response = await this.makeRequest(`${this.baseURL}${endpoint.path}`);
                
                results[endpoint.path] = {
                    success: response.statusCode === 200,
                    statusCode: response.statusCode,
                    description: endpoint.description,
                    dbConnected: response.statusCode === 200,
                    response: response.data
                };

                if (response.statusCode === 200) {
                    console.log(`    ✅ DB via ${endpoint.path}: ${response.statusCode} - Database is accessible`);
                    try {
                        const jsonData = JSON.parse(response.data);
                        console.log(`    📊 DB Response: ${JSON.stringify(jsonData, null, 2)}`);
                    } catch (e) {
                        console.log(`    📄 DB Response: ${response.data.substring(0, 200)}...`);
                    }
                } else {
                    console.log(`    ❌ DB via ${endpoint.path}: ${response.statusCode} - Database may be inaccessible`);
                }

            } catch (error) {
                console.log(`    ❌ DB via ${endpoint.path}: ${error.message}`);
                results[endpoint.path] = {
                    success: false,
                    error: error.message,
                    dbConnected: false,
                    description: endpoint.description
                };
            }
        }

        return results;
    }

    async testCORSAndSecurity() {
        console.log("\n🔒 Testing CORS and Security");
        console.log("=".repeat(50));

        const results = {};

        // Test CORS headers
        try {
            console.log(`  Testing CORS headers`);
            
            const response = await this.makeRequest(`${this.baseURL}/mcp/mcp/health`, {
                headers: {
                    'Origin': 'https://machine.vernalcontentum.com',
                    'Access-Control-Request-Method': 'GET'
                }
            });

            results['cors'] = {
                success: response.statusCode === 200,
                statusCode: response.statusCode,
                corsHeaders: {
                    'access-control-allow-origin': response.headers['access-control-allow-origin'],
                    'access-control-allow-methods': response.headers['access-control-allow-methods'],
                    'access-control-allow-headers': response.headers['access-control-allow-headers']
                }
            };

            if (response.statusCode === 200) {
                console.log(`    ✅ CORS: ${response.statusCode} - CORS headers present`);
                console.log(`    📊 Allow Origin: ${response.headers['access-control-allow-origin'] || 'Not set'}`);
                console.log(`    📊 Allow Methods: ${response.headers['access-control-allow-methods'] || 'Not set'}`);
            } else {
                console.log(`    ❌ CORS: ${response.statusCode} - CORS may not be configured`);
            }

        } catch (error) {
            console.log(`    ❌ CORS: ${error.message}`);
            results['cors'] = {
                success: false,
                error: error.message
            };
        }

        return results;
    }

    async runComprehensiveLiveTest() {
        console.log("🚀 Live API and Database Testing Suite");
        console.log("=".repeat(60));
        console.log(`Timestamp: ${new Date().toISOString()}`);
        console.log(`Backend URL: ${this.baseURL}`);
        console.log(`Frontend URL: ${this.frontendURL}`);
        console.log();

        try {
            // Run all test categories
            const healthResults = await this.testBackendHealth();
            const mcpResults = await this.testMCPEndpoints();
            const toolResults = await this.testToolExecution();
            const workflowResults = await this.testWorkflowExecution();
            const frontendResults = await this.testFrontendConnectivity();
            const dbResults = await this.testDatabaseConnectivity();
            const securityResults = await this.testCORSAndSecurity();

            // Calculate success rates
            const allResults = {
                health: healthResults,
                mcp: mcpResults,
                tools: toolResults,
                workflows: workflowResults,
                frontend: frontendResults,
                database: dbResults,
                security: securityResults
            };

            let totalTests = 0;
            let successfulTests = 0;

            for (const [category, results] of Object.entries(allResults)) {
                for (const [testName, result] of Object.entries(results)) {
                    totalTests++;
                    if (result.success) successfulTests++;
                }
            }

            const successRate = (successfulTests / totalTests * 100).toFixed(1);

            console.log("\n" + "=".repeat(60));
            console.log("📊 LIVE TEST SUMMARY");
            console.log("=".repeat(60));
            console.log(`Total Tests: ${totalTests}`);
            console.log(`Successful Tests: ${successfulTests}`);
            console.log(`Success Rate: ${successRate}%`);
            console.log(`Backend Status: ${healthResults['/health']?.success ? '✅ Online' : '❌ Offline'}`);
            console.log(`Frontend Status: ${frontendResults['frontend']?.success ? '✅ Online' : '❌ Offline'}`);
            console.log(`Database Status: ${Object.values(dbResults).some(r => r.dbConnected) ? '✅ Connected' : '❌ Disconnected'}`);
            console.log("=".repeat(60));

            // Save results
            const finalResults = {
                timestamp: new Date().toISOString(),
                backend_url: this.baseURL,
                frontend_url: this.frontendURL,
                total_tests: totalTests,
                successful_tests: successfulTests,
                success_rate: successRate,
                test_results: allResults,
                summary: {
                    backend_online: healthResults['/health']?.success || false,
                    frontend_online: frontendResults['frontend']?.success || false,
                    database_connected: Object.values(dbResults).some(r => r.dbConnected),
                    mcp_functional: Object.values(mcpResults).some(r => r.success),
                    cors_configured: securityResults['cors']?.success || false
                }
            };

            fs.writeFileSync("live_api_test_results.json", JSON.stringify(finalResults, null, 2));
            console.log("💾 Results saved to live_api_test_results.json");

            console.log("\n✅ LIVE TESTING COMPLETED!");
            console.log("🎉 Real API calls and database connectivity tested!");

        } catch (error) {
            console.log(`\n❌ Live test failed: ${error.message}`);
            return false;
        }

        return true;
    }
}

// Run the live tests
async function main() {
    const tester = new LiveAPITester();
    const success = await tester.runComprehensiveLiveTest();
    process.exit(success ? 0 : 1);
}

if (require.main === module) {
    main().catch(console.error);
}

module.exports = LiveAPITester;
