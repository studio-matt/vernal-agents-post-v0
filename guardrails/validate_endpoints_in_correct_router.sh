#!/bin/bash
# Validate that endpoints are in the correct router files
# Prevents cross-contamination like brand_personalities endpoints in author_personalities.py

set -e

echo "🔍 Validating endpoints are in correct router files..."
echo ""

ERRORS=0

# Define router-to-path mapping
declare -A ROUTER_PATHS
ROUTER_PATHS["author_personalities"]="/author_personalities"
ROUTER_PATHS["brand_personalities"]="/brand_personalities"
ROUTER_PATHS["campaigns"]="/campaigns"
ROUTER_PATHS["campaigns_research"]="/campaigns.*research"
ROUTER_PATHS["content"]="/content|/analyze|/generate|/schedule|/image"
ROUTER_PATHS["platforms"]="/platforms"
ROUTER_PATHS["admin"]="/admin"

# Check each router file
for router_file in app/routes/*.py; do
    if [ ! -f "$router_file" ]; then
        continue
    fi
    
    router_name=$(basename "$router_file" .py)
    echo "📁 Checking $router_name router..."
    
    # Get expected path for this router
    expected_path="${ROUTER_PATHS[$router_name]}"
    
    if [ -z "$expected_path" ]; then
        echo "   ⚠️  No path mapping defined for $router_name (add to script)"
        continue
    fi
    
    # Find all endpoint decorators in this file
    while IFS= read -r line; do
        # Extract the path from the decorator
        if echo "$line" | grep -qE "@.*_router\.(get|post|put|delete|patch)\([\"']([^\"']+)[\"']"; then
            endpoint_path=$(echo "$line" | sed -E "s/.*@.*_router\.(get|post|put|delete|patch)\([\"']([^\"']+)[\"'].*/\2/")
            
            # Check if this path belongs to this router
            if echo "$endpoint_path" | grep -qE "$expected_path"; then
                echo "   ✅ $endpoint_path (correct)"
            else
                # Check if it belongs to another router
                found_in_other=false
                for other_router in "${!ROUTER_PATHS[@]}"; do
                    if [ "$other_router" != "$router_name" ]; then
                        other_path="${ROUTER_PATHS[$other_router]}"
                        if echo "$endpoint_path" | grep -qE "$other_path"; then
                            echo "   ❌ $endpoint_path (belongs in $other_router router, found in $router_name)"
                            ERRORS=$((ERRORS + 1))
                            found_in_other=true
                            break
                        fi
                    fi
                done
                
                if [ "$found_in_other" = false ]; then
                    echo "   ⚠️  $endpoint_path (unknown router mapping)"
                fi
            fi
        fi
    done < "$router_file"
done

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "✅ All endpoints are in correct router files"
    exit 0
else
    echo "❌ Found $ERRORS endpoint(s) in wrong router files"
    echo ""
    echo "Fix: Move endpoints to their correct router files"
    exit 1
fi

