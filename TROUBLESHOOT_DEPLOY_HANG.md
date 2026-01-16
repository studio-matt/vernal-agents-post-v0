# Troubleshooting Deploy Script Hangs

## Common Hang Points

### 1. `pip install -r requirements.txt` (Most Common)
**Symptoms:** Script hangs at dependency installation
**Causes:**
- Slow network connection
- Package download timeouts
- Large packages (crewai, openai, etc.)

**Solutions:**
```bash
# Run pip install separately to see progress
cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate
pip install -r requirements.txt --no-cache-dir

# Or increase timeout in script
timeout 600 pip install -r requirements.txt --no-cache-dir -q
```

### 2. `systemctl restart vernal-agents` (No Timeout!)
**Symptoms:** Script hangs indefinitely at service restart
**Causes:**
- Service fails to start (syntax errors, import errors)
- Service stuck in "activating" state
- Missing .env file

**Solutions:**
```bash
# Check service status
sudo systemctl status vernal-agents

# Check logs for errors
sudo journalctl -u vernal-agents --since "5 minutes ago" | tail -50

# Check if .env exists
ls -la /home/ubuntu/vernal-agents-post-v0/.env

# Try starting manually
sudo systemctl start vernal-agents
sudo systemctl status vernal-agents
```

### 3. `python3 scripts/insert_visualizer_settings.py`
**Symptoms:** Script hangs at visualizer settings insertion
**Causes:**
- Database connection timeout
- Database credentials incorrect
- Database server unreachable

**Solutions:**
```bash
# Run script separately to see errors
cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate
python3 scripts/insert_visualizer_settings.py

# Check database connection
python3 -c "from database import SessionLocal; db = SessionLocal(); print('DB OK')"
```

### 4. `curl http://127.0.0.1:8000/health`
**Symptoms:** Script hangs at health check
**Causes:**
- Service not started yet
- Port 8000 not listening
- Service crashed immediately after start

**Solutions:**
```bash
# Check if port is listening
sudo lsof -i :8000

# Check service status
sudo systemctl status vernal-agents

# Check logs
sudo journalctl -u vernal-agents --since "2 minutes ago" | tail -50
```

## Quick Diagnostic Commands

```bash
# 1. Check which step is running
ps aux | grep -E "git|pip|python3|systemctl|curl" | grep -v grep

# 2. Check service status
sudo systemctl status vernal-agents

# 3. Check if port is listening
sudo lsof -i :8000

# 4. Check recent logs
sudo journalctl -u vernal-agents --since "10 minutes ago" | tail -100

# 5. Check for syntax errors
cd /home/ubuntu/vernal-agents-post-v0
bash find_all_syntax_errors.sh
```

## Improved Deploy Script

Use `deploy_with_diagnostics.sh` which:
- Shows progress for each step
- Has timeouts on all steps
- Provides diagnostic output
- Continues even if non-critical steps fail

```bash
cd /home/ubuntu/vernal-agents-post-v0
bash deploy_with_diagnostics.sh
```

## Manual Step-by-Step Deploy

If script keeps hanging, deploy manually:

```bash
cd /home/ubuntu/vernal-agents-post-v0

# Step 1: Pull code
git fetch origin
git switch main
git pull origin main

# Step 2: Install dependencies (run in background or separate terminal)
source venv/bin/activate
pip install -r requirements.txt --no-cache-dir

# Step 3: Insert settings (optional - can skip if it hangs)
python3 scripts/insert_visualizer_settings.py || echo "Settings insert failed, continuing..."

# Step 4: Restart service
sudo systemctl restart vernal-agents

# Step 5: Wait and check
sleep 10
sudo systemctl status vernal-agents
curl http://127.0.0.1:8000/health
```

