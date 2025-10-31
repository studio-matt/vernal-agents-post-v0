# 🚀 Emergency Net Compliant Deployment - Phase 1 (Dependency Validation)

**Date:** $(date)  
**Changes:** Added spacy, duckduckgo-search, validate_dependencies.py script  
**Type:** Long Reboot (new dependencies + validation script)

---

## ✅ EMERGENCY NET COMPLIANT DEPLOYMENT COMMANDS

### **OPTION A: Automated Script (RECOMMENDED - Handles Everything)**

**SSH to backend server first:**
```bash
ssh ubuntu@18.235.104.132
```

**Then run the bulletproof deployment script:**
```bash
cd /home/ubuntu
rm -rf /home/ubuntu/vernal-agents-post-v0 2>/dev/null || true
git clone https://github.com/studio-matt/vernal-agents-post-v0.git /home/ubuntu/vernal-agents-post-v0
cd /home/ubuntu/vernal-agents-post-v0
chmod +x scripts/bulletproof_deploy_backend.sh
bash scripts/bulletproof_deploy_backend.sh
```

**After script completes, download spaCy model:**
```bash
cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate
python -m spacy download en_core_web_md
```

---

### **OPTION B: Manual Step-by-Step (If You Prefer Control)**

**SSH to backend server first:**
```bash
ssh ubuntu@18.235.104.132
```

**Then run these commands in order:**

```bash
# 1. Pull Latest Code
cd /home/ubuntu/vernal-agents-post-v0
git fetch origin && git switch main && git pull --ff-only origin main

# 2. MANDATORY: Validate Dependencies (PREVENTS DEPENDENCY HELL)
python3 validate_dependencies.py || {
    echo "❌ Dependency validation FAILED. Fix issues before proceeding."
    exit 1
}

# 3. Activate Virtual Environment
source venv/bin/activate

# 4. Install Dependencies (includes new spacy, duckduckgo-search)
pip install -r requirements.txt --no-cache-dir

# 5. Download spaCy Language Model (REQUIRED for NLP processing)
python -m spacy download en_core_web_md

# 6. Restart Systemd Service
sudo systemctl restart vernal-agents
sudo systemctl status vernal-agents

# 7. Verification (MANDATORY)
sleep 5
curl -s http://127.0.0.1:8000/health | jq .
curl -s http://127.0.0.1:8000/mcp/enhanced/health | jq .
curl -I https://themachine.vernalcontentum.com/health
curl -I https://themachine.vernalcontentum.com/auth/login
```

---

## ✅ ONE-LINER (Copy-Paste Friendly)

**If you prefer to copy-paste everything at once:**

```bash
ssh ubuntu@18.235.104.132 << 'DEPLOY_EOF'
cd /home/ubuntu/vernal-agents-post-v0 && \
git fetch origin && git switch main && git pull --ff-only origin main && \
python3 validate_dependencies.py && \
source venv/bin/activate && \
pip install -r requirements.txt --no-cache-dir && \
python -m spacy download en_core_web_md && \
sudo systemctl restart vernal-agents && \
sleep 5 && \
curl -s http://127.0.0.1:8000/health | jq . && \
curl -s http://127.0.0.1:8000/mcp/enhanced/health | jq . && \
echo "✅ Deployment complete!"
DEPLOY_EOF
```

---

## 🔍 What This Deployment Includes

1. ✅ **validate_dependencies.py** - Prevents dependency hell by validating before install
2. ✅ **spacy>=3.7.0** - NLP for entity extraction, dependency parsing, word vectors
3. ✅ **duckduckgo-search>=6.0.0** - Free search API for enhanced query searching
4. ✅ **playwright>=1.40.0** - Web scraping (already in requirements.txt)
5. ✅ **beautifulsoup4>=4.12.3** - HTML parsing (already in requirements.txt)
6. ✅ **lxml>=4.9.3** - XML/HTML processing (already in requirements.txt)
7. ✅ **spaCy model (en_core_web_md)** - Required for NLP features

---

## ⚠️ IMPORTANT NOTES

- **Validation must pass** - If `validate_dependencies.py` fails, deployment is BLOCKED
- **This is a LONG REBOOT** - New dependencies require full installation
- **spaCy model download** - Takes ~30 seconds to download ~40MB model
- **Service restart** - Backend will be down for ~10-15 seconds during restart
- **Health checks** - All verification steps must pass before considering deployment complete

---

## 🚨 If Deployment Fails

1. Check validation output: `python3 validate_dependencies.py`
2. Check systemd logs: `sudo journalctl -u vernal-agents -f`
3. Verify .env exists: `ls -la /home/ubuntu/vernal-agents-post-v0/.env`
4. Verify database connectivity: `curl -s http://127.0.0.1:8000/mcp/enhanced/health`

---

**Emergency Net Compliant ✅**  
**Last Updated:** $(date)  
**Reference:** `backend-repo/docs/EMERGENCY_NET.md` Sections 375-465

