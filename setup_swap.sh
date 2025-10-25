#!/bin/bash
# Setup swap space to prevent OOM kills during deployment

set -e

echo "💾 Setting up swap space to prevent OOM kills..."

# Check if swap already exists
if swapon --show | grep -q "/swapfile"; then
    echo "✅ Swap already exists"
    swapon --show
    exit 0
fi

# Create 8GB swap file
echo "📦 Creating 8GB swap file..."
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make swap permanent
echo "🔧 Making swap permanent..."
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verify swap is active
echo "✅ Swap space configured:"
swapon --show
free -h

echo "🎉 Swap space setup complete!"
