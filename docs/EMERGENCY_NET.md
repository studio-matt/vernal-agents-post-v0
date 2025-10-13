# Vernal Agents Backend — Emergency Net

## TL;DR
- **App:** FastAPI served by Python (systemd)
- **Domain:** https://themachine.vernalcontentum.com → **nginx** → `127.0.0.1:8000`
- **Live dir:** `/home/ubuntu/vernal-agents-post-v0`
- **Repo:** https://github.com/studio-matt/vernal-agents-post-v0.git
- **DB:** MySQL (remote @ `50.6.198.220:3306`)
- **Service:** `vernal-agents.service` (systemd) ← **CURRENT WORKING SERVICE**
- **Health:**  
  - Local:  `curl -s http://127.0.0.1:8000/config/test` → `{"detail":"Agent or Task not found"}` (DB connected)
  - Public: `curl -s https://themachine.vernalcontentum.com/config/test` → `{"detail":"Agent or Task not found"}` (DB connected)

---

## Key Paths
- **Project:** `/home/ubuntu/vernal-agents-post-v0`
- **Virtualenv:** `/home/ubuntu/vernal-agents-post-v0/venv/`
- **Systemd unit:** `/etc/systemd/system/vernal-agents.service` ← **CURRENT WORKING**
  - Logs: `sudo journalctl -u vernal-agents.service -n 120 --no-pager`
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
- **Known Issues:** 
  - Missing `get_all_campaigns` method in DatabaseManager
  - Missing auth endpoints (`/auth/signup`, `/auth/login`)
  - `db_manager.create_tables()` commented out (method doesn't exist)

---

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
