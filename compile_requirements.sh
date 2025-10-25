#!/bin/bash
# compile_requirements.sh - Generate locked requirements using pip-compile

echo "🔧 COMPILING LOCKED REQUIREMENTS..."

# Upgrade build tools for Python 3.11 compatibility
echo "⬆️ Upgrading build tools..."
pip install --upgrade pip setuptools wheel

# Install pip-tools if not available
echo "📦 Installing pip-tools..."
pip install pip-tools

# Compile requirements from .in file
echo "📦 Compiling requirements from requirements.in..."
pip-compile requirements.in --output-file requirements-locked.txt

# Show the results
echo "✅ Generated requirements-locked.txt"
echo "📋 Summary:"
wc -l requirements-locked.txt
echo "🔍 First 10 lines:"
head -10 requirements-locked.txt

# Test the locked requirements
echo "🧪 Testing locked requirements..."
pip install -r requirements-locked.txt
pip check

echo "🎉 Requirements compilation complete!"
