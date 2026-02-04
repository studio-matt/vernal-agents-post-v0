# Backend Repo Path on AWS Server

**Canonical path (from EMERGENCY_NET_BACKEND.md):**

```text
/home/ubuntu/vernal-agents-post-v0
```

- **WorkingDirectory** (systemd): `/home/ubuntu/vernal-agents-post-v0`
- **ExecStart:** `/home/ubuntu/vernal-agents-post-v0/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000`

## Run Debug Scripts

```bash
cd /home/ubuntu/vernal-agents-post-v0
bash scripts/debug_campaigns_slow.sh
bash scripts/check_campaigns_db.sh
```

## Verify Path

```bash
sudo systemctl status vernal-agents | grep -i "working\|directory"
# Or:
sudo cat /etc/systemd/system/vernal-agents.service | grep -i "working\|directory\|execstart"
```
