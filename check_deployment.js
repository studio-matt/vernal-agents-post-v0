/**
 * Deployment Status Checker
 * Monitors deployment progress and provides detailed status
 */

const https = require('https');
const fs = require('fs');

class DeploymentChecker {
    constructor() {
        this.backendURL = 'https://themachine.vernalcontentum.com';
        this.frontendURL = 'https://machine.vernalcontentum.com';
        this.githubAPI = 'https://api.github.com/repos/studio-matt/vernal-agents-post-v0/actions/runs';
    }

    async checkBackendStatus() {
        console.log("🔍 Checking Backend Deployment Status");
        console.log("=".repeat(50));
        
        const endpoints = [
            '/health',
            '/mcp/mcp/health', 
            '/mcp/enhanced/health'
        ];

        let backendOnline = false;
        let workingEndpoints = [];

        for (const endpoint of endpoints) {
            try {
                const response = await this.makeRequest(`${this.backendURL}${endpoint}`);
                
                if (response.statusCode === 200) {
                    backendOnline = true;
                    workingEndpoints.push(endpoint);
                    console.log(`  ✅ ${endpoint}: ${response.statusCode} - Working`);
                    
                    try {
                        const jsonData = JSON.parse(response.data);
                        console.log(`    📊 Response: ${JSON.stringify(jsonData, null, 2)}`);
                    } catch (e) {
                        console.log(`    📄 Response: ${response.data.substring(0, 100)}...`);
                    }
                } else {
                    console.log(`  ❌ ${endpoint}: ${response.statusCode} - ${response.data.substring(0, 50)}...`);
                }
            } catch (error) {
                console.log(`  ❌ ${endpoint}: ${error.message}`);
            }
        }

        return {
            backendOnline,
            workingEndpoints,
            status: backendOnline ? 'DEPLOYED' : 'DEPLOYING'
        };
    }

    async checkFrontendStatus() {
        console.log("\n🌐 Checking Frontend Status");
        console.log("=".repeat(50));
        
        try {
            const response = await this.makeRequest(this.frontendURL);
            
            if (response.statusCode === 200) {
                console.log(`  ✅ Frontend: ${response.statusCode} - Online`);
                console.log(`  📊 Content Type: ${response.headers['content-type']}`);
                console.log(`  📊 Content Length: ${response.data.length} bytes`);
                
                if (response.data.includes('Vernal Contentum') && response.data.includes('Login')) {
                    console.log(`  ✅ Login page detected - Frontend working correctly`);
                }
                
                return { frontendOnline: true, status: 'ONLINE' };
            } else {
                console.log(`  ❌ Frontend: ${response.statusCode} - ${response.data}`);
                return { frontendOnline: false, status: 'OFFLINE' };
            }
        } catch (error) {
            console.log(`  ❌ Frontend: ${error.message}`);
            return { frontendOnline: false, status: 'ERROR' };
        }
    }

    async checkGitHubActions() {
        console.log("\n🔄 Checking GitHub Actions Status");
        console.log("=".repeat(50));
        
        try {
            // Note: This would require authentication in a real scenario
            console.log("  ℹ️  GitHub Actions status check requires authentication");
            console.log("  ℹ️  Check manually at: https://github.com/studio-matt/vernal-agents-post-v0/actions");
            console.log("  ℹ️  Look for recent runs on the 'mcp-conversion' branch");
            
            return {
                status: 'MANUAL_CHECK_REQUIRED',
                url: 'https://github.com/studio-matt/vernal-agents-post-v0/actions'
            };
        } catch (error) {
            console.log(`  ❌ GitHub Actions check failed: ${error.message}`);
            return { status: 'ERROR', error: error.message };
        }
    }

    async checkDeploymentProgress() {
        console.log("\n⏱️  Monitoring Deployment Progress");
        console.log("=".repeat(50));
        
        const maxChecks = 5;
        const checkInterval = 10000; // 10 seconds
        
        for (let i = 1; i <= maxChecks; i++) {
            console.log(`\n🔄 Check ${i}/${maxChecks} - ${new Date().toISOString()}`);
            
            const backendStatus = await this.checkBackendStatus();
            
            if (backendStatus.backendOnline) {
                console.log("\n🎉 DEPLOYMENT SUCCESSFUL!");
                console.log("✅ Backend is now online and responding");
                return { success: true, attempts: i };
            }
            
            if (i < maxChecks) {
                console.log(`⏳ Waiting ${checkInterval/1000} seconds before next check...`);
                await new Promise(resolve => setTimeout(resolve, checkInterval));
            }
        }
        
        console.log("\n⚠️  DEPLOYMENT STILL IN PROGRESS");
        console.log("❌ Backend not responding after maximum checks");
        return { success: false, attempts: maxChecks };
    }

    async makeRequest(url, options = {}) {
        return new Promise((resolve, reject) => {
            const isHttps = url.startsWith('https://');
            const client = isHttps ? https : http;
            
            const requestOptions = {
                method: options.method || 'GET',
                headers: {
                    'User-Agent': 'Deployment-Checker/1.0',
                    ...options.headers
                },
                timeout: options.timeout || 5000
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

    async runDeploymentCheck() {
        console.log("🚀 Deployment Status Checker");
        console.log("=".repeat(60));
        console.log(`Timestamp: ${new Date().toISOString()}`);
        console.log(`Backend URL: ${this.backendURL}`);
        console.log(`Frontend URL: ${this.frontendURL}`);
        console.log();

        try {
            // Check current status
            const backendStatus = await this.checkBackendStatus();
            const frontendStatus = await this.checkFrontendStatus();
            const githubStatus = await this.checkGitHubActions();

            console.log("\n" + "=".repeat(60));
            console.log("📊 CURRENT STATUS");
            console.log("=".repeat(60));
            console.log(`Backend: ${backendStatus.status}`);
            console.log(`Frontend: ${frontendStatus.status}`);
            console.log(`GitHub Actions: ${githubStatus.status}`);
            console.log("=".repeat(60));

            // If backend is not online, monitor deployment progress
            if (!backendStatus.backendOnline) {
                console.log("\n🔄 Backend not online - monitoring deployment progress...");
                const progressResult = await this.checkDeploymentProgress();
                
                if (progressResult.success) {
                    console.log("\n🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!");
                    console.log("✅ Enhanced MCP backend is now live and ready for testing");
                } else {
                    console.log("\n⚠️  DEPLOYMENT STILL IN PROGRESS");
                    console.log("💡 Check GitHub Actions manually or wait longer");
                    console.log("🔗 GitHub Actions: https://github.com/studio-matt/vernal-agents-post-v0/actions");
                }
            } else {
                console.log("\n✅ Backend is already online and ready for testing!");
            }

            // Save status report
            const statusReport = {
                timestamp: new Date().toISOString(),
                backend: backendStatus,
                frontend: frontendStatus,
                github: githubStatus,
                deployment_complete: backendStatus.backendOnline
            };

            fs.writeFileSync("deployment_status.json", JSON.stringify(statusReport, null, 2));
            console.log("\n💾 Status report saved to deployment_status.json");

        } catch (error) {
            console.log(`\n❌ Deployment check failed: ${error.message}`);
            return false;
        }

        return true;
    }
}

// Run the deployment check
async function main() {
    const checker = new DeploymentChecker();
    const success = await checker.runDeploymentCheck();
    process.exit(success ? 0 : 1);
}

if (require.main === module) {
    main().catch(console.error);
}

module.exports = DeploymentChecker;
