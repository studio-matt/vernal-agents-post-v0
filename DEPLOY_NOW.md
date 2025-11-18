# 🚀 Deploy Now - GitHub 500 Error Workaround

## Problem
GitHub is returning 500 errors, preventing `git pull` from working.

## Solution 1: Deploy Without Pulling (Recommended)

If your code is already up to date, use this one-liner:

```bash
cd /home/ubuntu/vernal-agents-post-v0 && source venv/bin/activate && pip install -r requirements.txt --no-cache-dir -q && (python3 scripts/insert_visualizer_settings.py || echo "⚠️  Script failed, continuing...") && sudo systemctl restart vernal-agents && sleep 3 && curl -s http://127.0.0.1:8000/health | jq -r '.status // "ok"' && echo "✅ Deploy complete"
```

Or use the script:
```bash
cd /home/ubuntu/vernal-agents-post-v0 && bash scripts/short_deploy_no_pull.sh
```

## Solution 2: Retry with Error Handling

Use this one-liner that continues even if git pull fails:

```bash
cd /home/ubuntu/vernal-agents-post-v0 && (git fetch origin && git switch main && git pull --ff-only origin main || echo "⚠️  Git pull failed, continuing...") && source venv/bin/activate && pip install -r requirements.txt --no-cache-dir -q && (python3 scripts/insert_visualizer_settings.py || echo "⚠️  Script failed, continuing...") && sudo systemctl restart vernal-agents && sleep 3 && curl -s http://127.0.0.1:8000/health | jq -r '.status // "ok"' && echo "✅ Deploy complete"
```

## Solution 3: Wait and Retry

GitHub 500 errors are usually temporary. Wait 5-10 minutes and try again:

```bash
cd /home/ubuntu/vernal-agents-post-v0 && git fetch origin && git switch main && git pull --ff-only origin main && source venv/bin/activate && pip install -r requirements.txt --no-cache-dir -q && python3 scripts/insert_visualizer_settings.py && sudo systemctl restart vernal-agents && sleep 3 && curl -s http://127.0.0.1:8000/health | jq -r '.status // "ok"' && echo "✅ Deploy complete"
```

## Check GitHub Status

Visit https://www.githubstatus.com/ to see if GitHub is experiencing issues.

