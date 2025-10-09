# Vernal Agents Backend — Emergency Net

## TL;DR
- **App:** FastAPI served by Uvicorn (systemd)
- **Domain:** https://themachine.vernalcontentum.com → **nginx** → `127.0.0.1:8000`
- **Live dir:** `/home/ubuntu/vernal-agents-post-v0`
- **Repo:** https://github.com/studio-matt/vernal-agents-post-v0.git
- **DB:** MySQL (remote @ `50.6.198.220:3306`)
- **Service:** `fastapi.service` (systemd)
- **Health:**  
  - Local:  `curl -s http://127.0.0.1:8000/health` → `{"ok":true}`  
  - Public: `curl -s https://themachine.vernalcontentum.com/health` → `{"ok":true}`

---

## Key Paths
- **Project:** `/home/ubuntu/vernal-agents-post-v0`
- **Virtualenv:** `/home/ubuntu/vernal-agents-post-v0/venv/`
- **Systemd unit:** `/etc/systemd/system/fastapi.service`  
  - Logs: `sudo journalctl -u fastapi.service -n 120 --no-pager`
- **nginx site:** `/etc/nginx/sites-enabled/themachine`  
  - Proxies → `http://127.0.0.1:8000`
  - TLS → `/etc/letsencrypt/live/themachine.vernalcontentum.com/`
  - CORS + rate limit in site + `/etc/nginx/conf.d/vernal_limits.conf`
- **Health endpoint:** `/health` (excluded from redirect logic)

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
