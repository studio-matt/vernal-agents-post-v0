#!/bin/bash
# compile_requirements.sh - Generate locked requirements using pip-compile
# EMERGENCY NET COMPLIANT: Follows all dependency management rules

echo "🔧 COMPILING LOCKED REQUIREMENTS (Emergency Net Compliant)..."

# CRITICAL: Pin pip<25.0 BEFORE installing pip-tools (Emergency Net requirement)
echo "⬇️ Pinning pip<25.0 for pip-tools compatibility..."
pip install "pip<25.0" setuptools wheel

# Install pip-tools if not available
echo "📦 Installing pip-tools..."
pip install pip-tools

# Verify pip version is correct
echo "🔍 Verifying pip version..."
pip --version | grep -q "pip 2[0-4]" || {
    echo "❌ ERROR: pip version must be <25.0 for pip-tools compatibility"
    echo "   Current version: $(pip --version)"
    exit 1
}

# CRITICAL: Use python -m piptools to ensure we use the installed version, not old global binary
# Compile requirements from .in file
echo "📦 Compiling requirements from requirements.in..."
python -m piptools compile requirements.in --output-file requirements-locked.txt

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
