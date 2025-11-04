#!/bin/bash
# Quick diagnostic script for scraping failures
# Usage: ./diagnose_scraping_failure.sh [CAMPAIGN_ID]

set -e

CAMPAIGN_ID="${1:-}"

if [ -z "$CAMPAIGN_ID" ]; then
    echo "❌ Usage: $0 <CAMPAIGN_ID>"
    echo "   Example: $0 31dfec2f-cce2-442a-b773-bf690074e2b0"
    exit 1
fi

echo "🔍 Diagnosing scraping failure for campaign: $CAMPAIGN_ID"
echo "=========================================="
echo ""

# Load environment variables
if [ -f /home/ubuntu/vernal-agents-post-v0/.env ]; then
    source /home/ubuntu/vernal-agents-post-v0/.env
else
    echo "⚠️  Warning: .env file not found, using environment variables"
fi

# Step 1: Check database for campaign data
echo "📊 Step 1: Checking database for campaign data..."
echo "---"

mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" <<EOF
SELECT 
    campaign_id,
    source_url,
    CASE 
        WHEN source_url LIKE 'error:%' THEN 'ERROR'
        WHEN source_url LIKE 'placeholder:%' THEN 'PLACEHOLDER'
        ELSE 'VALID'
    END as row_type,
    LENGTH(extracted_text) as text_length,
    fetched_at
FROM campaign_raw_data
WHERE campaign_id = '${CAMPAIGN_ID}'
ORDER BY fetched_at DESC
LIMIT 20;
EOF

echo ""
echo "📊 Summary:"
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" <<EOF
SELECT 
    COUNT(*) as total_rows,
    SUM(CASE WHEN source_url LIKE 'error:%' THEN 1 ELSE 0 END) as error_rows,
    SUM(CASE WHEN source_url LIKE 'placeholder:%' THEN 1 ELSE 0 END) as placeholder_rows,
    SUM(CASE WHEN source_url NOT LIKE 'error:%' AND source_url NOT LIKE 'placeholder:%' THEN 1 ELSE 0 END) as valid_rows,
    SUM(CASE WHEN source_url NOT LIKE 'error:%' AND source_url NOT LIKE 'placeholder:%' AND LENGTH(extracted_text) > 10 THEN 1 ELSE 0 END) as valid_text_rows
FROM campaign_raw_data
WHERE campaign_id = '${CAMPAIGN_ID}';
EOF

echo ""
echo "📋 Campaign status:"
mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" <<EOF
SELECT campaign_id, campaign_name, status, topics, created_at, updated_at
FROM campaign
WHERE campaign_id = '${CAMPAIGN_ID}';
EOF

echo ""
echo "=========================================="
echo ""

# Step 2: Check backend logs
echo "📋 Step 2: Checking backend logs for campaign..."
echo "---"
echo "Recent logs for campaign ${CAMPAIGN_ID}:"
echo ""

sudo journalctl -u vernal-agents --since "1 hour ago" | \
  grep -E "${CAMPAIGN_ID}" | \
  tail -50

echo ""
echo "=========================================="
echo ""

# Step 3: Check for scraping errors
echo "📋 Step 3: Checking for scraping errors..."
echo "---"
echo "Scraping-related errors:"
echo ""

sudo journalctl -u vernal-agents --since "1 hour ago" | \
  grep -E "scraping|CRITICAL|Scraping returned|All.*scraping attempts failed" | \
  tail -30

echo ""
echo "=========================================="
echo ""

# Step 4: Test Playwright availability
echo "📋 Step 4: Testing Playwright availability..."
echo "---"

cd /home/ubuntu/vernal-agents-post-v0
source venv/bin/activate

python3 <<EOF
import sys
try:
    from playwright.sync_api import sync_playwright
    print("✅ Playwright Python package imported successfully")
    p = sync_playwright().start()
    print(f"✅ Playwright started, chromium executable: {p.chromium.executable_path}")
    if p.chromium.executable_path and len(p.chromium.executable_path) > 0:
        print("✅ Chromium browser binaries installed")
    else:
        print("❌ Chromium browser binaries NOT installed")
        print("   Run: python -m playwright install chromium")
    p.stop()
except Exception as e:
    print(f"❌ Playwright error: {e}")
    sys.exit(1)
EOF

echo ""

# Step 5: Test DuckDuckGo availability
echo "📋 Step 5: Testing DuckDuckGo availability..."
echo "---"

python3 <<EOF
import sys
try:
    from duckduckgo_search import DDGS
    print("✅ DuckDuckGo Python package imported successfully")
    ddgs = DDGS()
    results = list(ddgs.text("test", max_results=1))
    if len(results) > 0:
        print(f"✅ DuckDuckGo search working: {len(results)} result(s)")
    else:
        print("⚠️  DuckDuckGo search returned 0 results (might be rate-limited)")
except Exception as e:
    print(f"❌ DuckDuckGo error: {e}")
    sys.exit(1)
EOF

echo ""
echo "=========================================="
echo "✅ Diagnostic complete!"
echo ""
echo "Next steps:"
echo "1. Review database results - if 0 valid_text_rows, scraping failed"
echo "2. Check logs for specific error messages"
echo "3. If Playwright/DuckDuckGo tests failed, fix those first"
echo "4. Re-run campaign and check logs again"

