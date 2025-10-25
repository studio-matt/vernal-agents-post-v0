#!/bin/bash
# Real-time RAM monitoring during deployment

echo "📊 Starting RAM monitoring..."

# Function to check memory and warn if low
check_memory() {
    AVAILABLE_MEM=$(free -m | awk 'NR==2{printf "%.0f", $7}')
    TOTAL_MEM=$(free -m | awk 'NR==2{printf "%.0f", $2}')
    USED_MEM=$(free -m | awk 'NR==2{printf "%.0f", $3}')
    SWAP_USED=$(free -m | awk 'NR==3{printf "%.0f", $3}')
    
    echo "📊 Memory Status:"
    echo "   Available: ${AVAILABLE_MEM}MB"
    echo "   Used: ${USED_MEM}MB / ${TOTAL_MEM}MB"
    echo "   Swap Used: ${SWAP_USED}MB"
    
    if [ "$AVAILABLE_MEM" -lt 500 ]; then
        echo "⚠️ WARNING: Low memory detected (${AVAILABLE_MEM}MB available)"
        echo "🧹 Running emergency cleanup..."
        sudo sync
        echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
        pip cache purge 2>/dev/null || true
        echo "📊 Memory after cleanup:"
        free -h
    fi
    
    if [ "$AVAILABLE_MEM" -lt 100 ]; then
        echo "🚨 CRITICAL: Very low memory (${AVAILABLE_MEM}MB available)"
        echo "🛑 Stopping deployment to prevent OOM kill"
        exit 1
    fi
}

# Monitor memory every 10 seconds
while true; do
    check_memory
    sleep 10
done
