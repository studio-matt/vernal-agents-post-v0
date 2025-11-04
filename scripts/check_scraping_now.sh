#!/bin/bash
# Quick diagnostic to check what's happening with scraping

CAMPAIGN_ID="${1:-31dfec2f-cce2-442a-b773-bf690074e2b0}"

echo "🔍 Checking scraping status for campaign: $CAMPAIGN_ID"
echo ""

# Check if dependencies are installed
echo "📦 Checking dependencies..."
source /home/ubuntu/vernal-agents-post-v0/venv/bin/activate
python -c "import bs4; import gensim; print('✅ bs4:', bs4.__version__); print('✅ gensim:', gensim.__version__)" 2>&1 || {
    echo "❌ Dependencies missing!"
    exit 1
}

echo ""
echo "📊 Checking database for campaign data..."
echo ""

# Check database rows
mysql -h 50.6.198.220 -u vernalcontentum_vernaluse -p$(grep DB_PASSWORD /home/ubuntu/vernal-agents-post-v0/.env | cut -d= -f2) vernalcontentum_contentMachine <<EOF
SELECT 
    COUNT(*) as total_rows,
    SUM(CASE WHEN source_url LIKE 'error:%' OR source_url LIKE 'placeholder:%' THEN 1 ELSE 0 END) as error_rows,
    SUM(CASE WHEN source_url NOT LIKE 'error:%' AND source_url NOT LIKE 'placeholder:%' AND LENGTH(extracted_text) > 10 THEN 1 ELSE 0 END) as valid_rows
FROM campaign_raw_data
WHERE campaign_id = '$CAMPAIGN_ID';

SELECT 
    source_url,
    CASE 
        WHEN source_url LIKE 'error:%' THEN 'ERROR'
        WHEN source_url LIKE 'placeholder:%' THEN 'PLACEHOLDER'
        ELSE 'VALID'
    END as row_type,
    LENGTH(extracted_text) as text_len,
    LEFT(extracted_text, 100) as text_sample
FROM campaign_raw_data
WHERE campaign_id = '$CAMPAIGN_ID'
ORDER BY fetched_at DESC
LIMIT 10;
EOF

echo ""
echo "📋 Checking recent backend logs for scraping activity..."
echo ""

# Check logs for scraping activity
sudo journalctl -u vernal-agents --since "10 minutes ago" | grep -E "$CAMPAIGN_ID|Scraped.*DB ID|bs4|gensim|ImportError|CRITICAL|ERROR.*scraping|Web scraping" | tail -30

echo ""
echo "✅ Diagnostic complete!"
echo ""
echo "If you see:"
echo "  - total_rows = 0: Scraping never ran or failed before saving"
echo "  - error_rows > 0, valid_rows = 0: Scraping ran but all failed"
echo "  - valid_rows > 0: Scraping succeeded, check frontend/API"

