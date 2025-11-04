#!/bin/bash
# test_playwright.sh - Test Playwright installation and browser launch

set -e

echo "🔍 Testing Playwright Installation"
echo "==================================="

cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate

echo ""
echo "1️⃣ Testing Playwright Python package import..."
python3 << 'PYEOF'
try:
    import playwright
    print("✅ playwright package imported")
except ImportError as e:
    print(f"❌ playwright package import failed: {e}")
    exit(1)
PYEOF

echo ""
echo "2️⃣ Testing Playwright sync_api import..."
python3 << 'PYEOF'
try:
    from playwright.sync_api import sync_playwright
    print("✅ playwright.sync_api imported")
except ImportError as e:
    print(f"❌ playwright.sync_api import failed: {e}")
    exit(1)
PYEOF

echo ""
echo "3️⃣ Testing Playwright browser launch..."
python3 << 'PYEOF'
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        print("✅ Chromium browser launched successfully")
        browser.close()
        print("✅ Browser closed successfully")
except Exception as e:
    print(f"❌ Browser launch failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
PYEOF

echo ""
echo "4️⃣ Testing web_scraping module import..."
python3 << 'PYEOF'
try:
    import sys
    sys.path.insert(0, '/home/ubuntu/vernal-agents-post-v0')
    from web_scraping import scrape_with_playwright
    print("✅ web_scraping module imported")
    print("✅ scrape_with_playwright function available")
except Exception as e:
    print(f"❌ web_scraping import failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
PYEOF

echo ""
echo "5️⃣ Testing actual scraping (test URL)..."
python3 << 'PYEOF'
try:
    import sys
    sys.path.insert(0, '/home/ubuntu/vernal-agents-post-v0')
    from web_scraping import scrape_with_playwright
    
    result = scrape_with_playwright("https://example.com", timeout=10000)
    if result.get("error"):
        print(f"❌ Scraping failed: {result['error']}")
        exit(1)
    elif result.get("text"):
        print(f"✅ Scraping successful! Got {len(result['text'])} characters")
    else:
        print("⚠️ Scraping returned no text")
except Exception as e:
    print(f"❌ Scraping test failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
PYEOF

echo ""
echo "✅ All Playwright tests passed!"

