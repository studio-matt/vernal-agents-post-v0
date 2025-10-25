# 🚀 Manual Deployment Guide

## When to Use Manual Deployment

Use this when GitHub Actions fails with **Status 137 (SIGKILL)** due to CI resource limits, or when you need guaranteed deployment completion.

## Prerequisites

- SSH access to your EC2 server
- Git access to the repository
- Sudo privileges on the server

## Manual Deployment Steps

### 1. SSH into the Server
```bash
ssh -i your-key.pem ubuntu@your-server-ip
```

### 2. Run the Deployment Script
```bash
# Navigate to home directory
cd /home/ubuntu

# Clone the latest code
git clone https://github.com/studio-matt/vernal-agents-post-v0.git /home/ubuntu/vernal-agents-post-v0

# Navigate to the project
cd /home/ubuntu/vernal-agents-post-v0

# Run the deployment script
chmod +x .github/workflows/deploy-agents.yml
# OR run the deployment steps manually (see below)
```

### 3. Manual Deployment Steps (if script fails)

```bash
# 1. Stop the service
sudo systemctl stop vernal-agents

# 2. Kill any stuck processes
sudo pkill -9 -f python || true
sudo pkill -9 -f uvicorn || true
sudo pkill -9 -f main.py || true

# 3. Remove old code
sudo rm -rf /home/ubuntu/vernal-agents-post-v0

# 4. Clone fresh code
git clone https://github.com/studio-matt/vernal-agents-post-v0.git /home/ubuntu/vernal-agents-post-v0
cd /home/ubuntu/vernal-agents-post-v0

# 5. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 6. Install dependencies with memory optimization
pip install --upgrade pip --no-cache-dir
pip install -r requirements.txt --no-cache-dir

# 7. Validate main.py
test -f main.py || { echo "ERROR: main.py not found!"; exit 1; }
grep -q "app = FastAPI" main.py || { echo "ERROR: main.py must define app = FastAPI()!"; exit 1; }

# 8. Set environment variables
export PYTHONPATH="/home/ubuntu/vernal-agents-post-v0:$PYTHONPATH"

# 9. Start the service
sudo systemctl start vernal-agents
sudo systemctl enable vernal-agents

# 10. Wait for service to start
sleep 10

# 11. Verify deployment
/home/ubuntu/verify_deployment.sh
```

## Verification Commands

### Check Service Status
```bash
sudo systemctl status vernal-agents
```

### Check Port 8000
```bash
netstat -tlnp | grep :8000
```

### Test Health Endpoints
```bash
# Local health check
curl http://localhost:8000/health

# Version check
curl http://localhost:8000/version

# Commit hash check
curl http://localhost:8000/deploy/commit

# External health check
curl https://themachine.vernalcontentum.com/health
```

### Check Completion Marker
```bash
cat /home/ubuntu/vernal_agents_deploy_complete.txt
```

### Run Full Verification
```bash
/home/ubuntu/verify_deployment.sh
```

## Troubleshooting

### If Service Won't Start
```bash
# Check logs
sudo journalctl -u vernal-agents -f

# Check for port conflicts
sudo lsof -i :8000

# Restart service
sudo systemctl restart vernal-agents
```

### If Port 8000 Not Listening
```bash
# Check if process is running
ps aux | grep python

# Check systemd status
sudo systemctl status vernal-agents

# Check for errors in main.py
python3 -c "import main; print('Import successful')"
```

### If External Access Fails
```bash
# Check nginx status
sudo systemctl status nginx

# Check nginx config
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

## Success Indicators

✅ **Deployment Complete When:**
- Service status shows "active (running)"
- Port 8000 is listening
- All health endpoints return 200 OK
- `/deploy/commit` returns the latest commit hash
- Completion marker file exists
- External access works

## Emergency Recovery

If everything fails:
1. Check server resources: `free -h`, `df -h`
2. Check system logs: `sudo journalctl -u vernal-agents`
3. Restart the server: `sudo reboot`
4. Run manual deployment steps after reboot

---

**Remember:** Manual deployment always works if your server has sufficient resources. The GitHub Action failure is purely a CI infrastructure limitation, not a code or script problem.
