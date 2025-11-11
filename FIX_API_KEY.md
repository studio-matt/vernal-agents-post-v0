# Fix OpenAI API Key Issue

## The Problem
The endpoint is working correctly, but the OpenAI API key is invalid or expired.

## Quick Fix

### Step 1: Check Current API Key
```bash
cd /home/ubuntu/vernal-agents-post-v0
grep OPENAI_API_KEY .env
```

### Step 2: Update API Key
```bash
# Edit the .env file
nano .env

# Find the line: OPENAI_API_KEY=sk-proj-...
# Replace with your valid API key from: https://platform.openai.com/account/api-keys
# Save and exit (Ctrl+X, then Y, then Enter)
```

### Step 3: Restart Service
```bash
sudo systemctl restart vernal-agents
```

### Step 4: Test Again
```bash
curl -X POST http://127.0.0.1:8000/mcp/generate-content \
  -H "Content-Type: application/json" \
  -d '{"text": "AI is changing business", "platform": "linkedin", "week": 1, "use_crewai": false}' | jq .
```

**Expected:** Should return `{"success": true}` with content.

---

## Alternative: Set API Key Directly (One-Liner)
```bash
cd /home/ubuntu/vernal-agents-post-v0
# Replace YOUR_API_KEY_HERE with your actual key
sed -i 's/OPENAI_API_KEY=.*/OPENAI_API_KEY=YOUR_API_KEY_HERE/' .env
sudo systemctl restart vernal-agents
```

---

## Verify API Key is Loaded
```bash
cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate
python3 -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API Key:', os.getenv('OPENAI_API_KEY')[:20] + '...' if os.getenv('OPENAI_API_KEY') else 'NOT SET')"
```

**Expected:** Should print the first 20 characters of your API key.

---

## Get a New API Key
1. Go to: https://platform.openai.com/account/api-keys
2. Click "Create new secret key"
3. Copy the key (starts with `sk-`)
4. Update your `.env` file with the new key
5. Restart the service

