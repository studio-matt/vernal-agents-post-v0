# 🚀 Emergency Net Compliant Deployment - Phase 2 (Web Scraping Implementation)

**Date:** $(date)  
**Changes:** Implemented real web scraping with DuckDuckGo + Playwright  
**Type:** Long Reboot (new code, requires Playwright browser installation)

---

## ✅ EMERGENCY NET COMPLIANT DEPLOYMENT COMMANDS

**Run these commands directly on the backend server terminal (you're already logged in).**

### **ONE-LINER (Copy-Paste Friendly)**

**Note:** Playwright Python package should already be installed from Phase 1. This only installs the browser binaries and updates code.

```bash
cd /home/ubuntu/vernal-agents-post-v0 && \
git fetch origin && git switch main && git pull --ff-only origin main && \
source venv/bin/activate && \
playwright install chromium && \
sudo systemctl restart vernal-agents && \
sleep 5 && \
curl -s http://127.0.0.1:8000/health | jq . && \
curl -s http://127.0.0.1:8000/mcp/enhanced/health | jq . && \
echo "✅ Phase 2 Deployment complete!"
```

---

### **MANUAL STEP-BY-STEP**

**Run these commands in order:**

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

# 4. Install Playwright Browser Binaries (REQUIRED for web scraping)
# Note: Playwright Python package already installed from Phase 1
# This only downloads the Chromium browser binaries (~170MB)
playwright install chromium

# 5. Restart Systemd Service
sudo systemctl restart vernal-agents
sudo systemctl status vernal-agents

# 6. Verification (MANDATORY)
sleep 5
curl -s http://127.0.0.1:8000/health | jq .
curl -s http://127.0.0.1:8000/mcp/enhanced/health | jq .
curl -I https://themachine.vernalcontentum.com/health
```

---

## 🔍 What This Deployment Includes

### **Phase 2 Changes:**

1. ✅ **New `web_scraping.py` module**:
   - DuckDuckGo search integration (`search_duckduckgo()`)
   - Playwright web scraping (`scrape_with_playwright()`)
   - Recursive scraping with depth control (`scrape_urls_recursive()`)
   - Main scraping function (`scrape_campaign_data()`)

2. ✅ **Updated `main.py`**:
   - Replaced placeholder data generation with real web scraping
   - Integrated all scraping settings (depth, max_pages, include_images, include_links)
   - Real-time progress reporting for scraping steps
   - Proper error handling and logging

3. ✅ **Settings Integration**:
   - `depth` - Controls link following (default: 1)
   - `max_pages` - Limits total pages scraped (default: 10)
   - `include_images` - Extracts image URLs if enabled
   - `include_links` - Extracts links for depth > 1 scraping
   - `keywords` + `query` - Combined for DuckDuckGo search
   - Direct `urls` - Scraped directly with Playwright

4. ✅ **Data Storage**:
   - Real scraped text stored in `CampaignRawData.extracted_text`
   - URLs stored in `CampaignRawData.source_url`
   - HTML stored in `CampaignRawData.raw_html` (if include_links=True)
   - Metadata stored in `CampaignRawData.meta_json` (images, links, depth, errors)

---

## ⚠️ IMPORTANT NOTES

- **Playwright Package vs Browsers**:
  - ✅ **Playwright Python package** (`playwright>=1.40.0`) - Already installed from Phase 1
  - ⚠️ **Playwright browser binaries** - Must be downloaded with `playwright install chromium`
  - This downloads Chromium browser (~170MB) needed for scraping
  - Without browser binaries, scraping will fail with "browser not installed" error
  - Takes ~1-2 minutes to download

- **This is a SHORT REBOOT** - Only code changes, no new dependencies
  - You can skip `pip install` and `validate_dependencies.py` if you're confident
  - Only need: pull code → install browser binaries → restart service

- **Service restart** - Backend will be down for ~10-15 seconds during restart

- **Scraping Performance**:
  - Each page takes ~5-10 seconds to scrape
  - With depth=1 and max_pages=10, expect ~1-2 minutes total scraping time
  - Progress updates will show real scraping steps

- **DuckDuckGo Rate Limiting**:
  - DuckDuckGo is free but may rate limit excessive requests
  - If search fails, check logs for rate limit errors

---

## 🧪 Testing After Deployment

**Test web scraping functionality:**

```bash
# 1. Check service is running
sudo systemctl status vernal-agents

# 2. Test DuckDuckGo search (in Python)
source venv/bin/activate
python3 -c "from web_scraping import search_duckduckgo; results = search_duckduckgo(['python', 'programming'], max_results=5); print(f'Found {len(results)} URLs: {results}')"

# 3. Test Playwright (if you have a test URL)
python3 -c "from web_scraping import scrape_with_playwright; result = scrape_with_playwright('https://example.com'); print(f'Scraped {len(result[\"text\"])} chars')"

# 4. Verify scraping works end-to-end by creating a test campaign in the UI
```

---

## 🚨 If Deployment Fails

1. **Check Playwright installation:**
   ```bash
   playwright --version
   playwright install chromium
   ```

2. **Check validation output:**
   ```bash
   python3 validate_dependencies.py
   ```

3. **Check systemd logs:**
   ```bash
   sudo journalctl -u vernal-agents -f
   ```

4. **Verify imports work:**
   ```bash
   source venv/bin/activate
   python3 -c "from web_scraping import scrape_campaign_data; print('✅ Import successful')"
   ```

---

**Emergency Net Compliant ✅**  
**Last Updated:** $(date)  
**Reference:** `backend-repo/docs/EMERGENCY_NET.md` Sections 375-465

