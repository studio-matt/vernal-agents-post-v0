# Vernal Agents Backend — Emergency Net

## TL;DR
- **App:** FastAPI served by Python (systemd)
- **Domain:** https://themachine.vernalcontentum.com → **nginx** → `127.0.0.1:8000`
- **Live dir:** `/home/ubuntu/vernal-agents-post-v0`
- **Repo:** https://github.com/studio-matt/vernal-agents-post-v0.git
- **DB:** MySQL (remote @ `50.6.198.220:3306`)
- **Service:** `vernal-agents.service` (systemd) ← **ONLY SERVICE - NO OTHERS**
- **Health:**  
  - Local:  `curl -s http://127.0.0.1:8000/config/test` → `{"detail":"Agent or Task not found"}` (DB connected)
  - Public: `curl -s https://themachine.vernalcontentum.com/config/test` → `{"detail":"Agent or Task not found"}` (DB connected)

---

## ⚠️ CRITICAL CONFIGURATION - NEVER CHANGE THESE ⚠️
- **Project:** `/home/ubuntu/vernal-agents-post-v0`
- **Virtualenv:** `/home/ubuntu/vernal-agents-post-v0/venv/`
- **Systemd unit:** `/etc/systemd/system/vernal-agents.service` ← **ONLY SERVICE**
- **ExecStart:** `/home/ubuntu/vernal-agents-post-v0/venv/bin/python main.py` ← **MUST USE VENV**
- **WorkingDirectory:** `/home/ubuntu/vernal-agents-post-v0` ← **MUST BE THIS PATH**
- **nginx site:** `/etc/nginx/sites-enabled/themachine`  
  - Proxies → `http://127.0.0.1:8000`
  - TLS → `/etc/letsencrypt/live/themachine.vernalcontentum.com/`
- **Environment:** `.env` file in project root with DB credentials

---

## Current Working Configuration (MCP Migration State)
- **Service:** `vernal-agents.service` (NOT `fastapi.service`)
- **ExecStart:** `/home/ubuntu/vernal-agents-post-v0/venv/bin/python main.py`
- **Database:** Connected and working (MySQL @ 50.6.198.220:3306)
- **Status:** Backend running, database connected, some methods missing
- **GitHub Actions Deployment:**
  - **Workflow:** `.github/workflows/agents-deploy-workflow.yml`
  - **Strategy:** Direct SSH deployment (pulls code, restarts service)
  - **GitHub Secrets Required:**
    - `EC2_HOST` = `18.235.104.132`
    - `EC2_USER` = `ubuntu`
    - `EC2_PRIVATE_KEY` = SSH private key for backend server
- **Known Issues:** 
  - Missing `get_all_campaigns` method in DatabaseManager
  - Missing auth endpoints (`/auth/signup`, `/auth/login`)
  - `db_manager.create_tables()` commented out (method doesn't exist)

---

## 🚨 SINGLE SOURCE OF TRUTH - USE THESE EXACT COMMANDS 🚨
```bash
# FIRST: Create virtual environment and install dependencies
cd /home/ubuntu/vernal-agents-post-v0
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# THEN: THE ONLY systemd service configuration that works:
sudo tee /etc/systemd/system/vernal-agents.service > /dev/null << 'EOF'
[Unit]
Description=Vernal Agents Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/vernal-agents-post-v0
ExecStart=/home/ubuntu/vernal-agents-post-v0/venv/bin/python main.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=/home/ubuntu/vernal-agents-post-v0

[Install]
WantedBy=multi-user.target
EOF

# Apply and start
sudo systemctl daemon-reload
sudo systemctl restart vernal-agents
```

## 🧹 CLEANUP COMMANDS - USE WHEN PORT 8000 IS BLOCKED
```bash
# Kill ALL competing processes on port 8000
sudo pkill -f "python.*main.py"
sudo pkill -f "uvicorn"
sudo kill -9 $(sudo lsof -t -i:8000) 2>/dev/null || true

# Verify port 8000 is free
sudo lsof -i :8000

# Start ONLY the systemd service
sudo systemctl start vernal-agents
sudo systemctl status vernal-agents
curl http://localhost:8000/health
```

## Quick Recovery Commands
```bash
# Check service status
sudo systemctl status vernal-agents

# Restart if needed
sudo systemctl restart vernal-agents

# Check logs
sudo journalctl -u vernal-agents -n 20 --no-pager

# Test database connectivity
curl http://localhost:8000/config/test
curl https://themachine.vernalcontentum.com/config/test
```

---

## Database Connectivity Test
- **Working:** Database connection, basic queries
- **Available methods:** `create_agent`, `create_task`, `get_agent_by_name`, `get_task_by_name`
- **Missing methods:** `get_all_campaigns`, `create_tables`
- **Test endpoint:** `PUT /agents/{agent_name}` (updates work)

---

## Previous Configuration (Pre-MCP Status) - COMMENTED OUT
<!-- 
PRE MCP STATUS - This was the working configuration before MCP migration:

- **Service:** `fastapi.service` (systemd) - INACTIVE
- **ExecStart:** `/home/ubuntu/vernal-agents-post-v0/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000`
- **EnvironmentFile:** `/etc/fastapi/vernal.env`
- **Health:** `curl -s http://127.0.0.1:8000/health` → `{"ok":true}`
- **Status:** Stopped 3 days ago, replaced by vernal-agents.service
- **Logs:** `sudo journalctl -u fastapi.service -n 120 --no-pager`

PRE MCP STATUS END
-->

---

## Migration Notes
- **Date:** October 2025
- **Reason:** MCP migration required direct Python execution instead of uvicorn
- **Change:** Switched from `fastapi.service` to `vernal-agents.service`
- **Database:** Same MySQL connection, different service configuration

---

## Runtime & Pinning (why gensim/scipy worked)
- **Python:** 3.12 (Ubuntu 24.04 LTS)
- **Pins that matter:**  
  - `numpy==1.26.4`  
  - `scipy==1.12.0`  ← required so `scipy.linalg.triu` exists (gensim compat)  
  - `gensim==4.3.2`  
  - `bertopic==0.16.3`  
  - `torch==2.2.2+cpu` / `torchvision==0.17.2+cpu`  
  - `smart-open>=6` (installed as `smart_open`)
- **Quick import check (optional):**
  ```bash
  /home/ubuntu/vernal-agents-post-v0/venv/bin/python - <<'PY'
import numpy, scipy, gensim; from bertopic import BERTopic
from scipy.linalg import triu
print("OK:", numpy.__version__, scipy.__version__, gensim.__version__)
PY
