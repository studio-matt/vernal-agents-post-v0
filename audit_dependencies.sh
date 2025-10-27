#!/bin/bash
# Systematic Dependency Audit Script
# This catches ALL dependency issues before CI/CD sees them

set -e

echo "🔍 STARTING SYSTEMATIC DEPENDENCY AUDIT..."

# Create a temporary virtual environment for testing
echo "📦 Creating temporary virtual environment..."
python3 -m venv /tmp/dependency_audit
source /tmp/dependency_audit/bin/activate

# Upgrade pip and install pip-tools
echo "⬆️ Upgrading pip and installing tools..."
pip install --upgrade pip
pip install pip-tools

# Test 1: Install all requirements and check for conflicts
echo "🧪 TEST 1: Installing all requirements..."
echo "Installing requirements-core.txt..."
pip install -r requirements-core.txt

echo "Installing requirements-ai.txt..."
pip install -r requirements-ai.txt

echo "Installing requirements-remaining.txt..."
pip install -r requirements-remaining.txt

# Test 2: Run pip check to find broken dependencies
echo "🧪 TEST 2: Running pip check for broken dependencies..."
if pip check; then
    echo "✅ No broken dependencies found"
else
    echo "❌ Broken dependencies found:"
    pip check
    exit 1
fi

# Test 3: Test without version pins
echo "🧪 TEST 3: Testing without version pins..."
echo "Creating temporary requirements without pins..."

# Create temporary files without version pins
sed 's/==[0-9].*//g' requirements-core.txt > /tmp/requirements-core-no-pins.txt
sed 's/==[0-9].*//g' requirements-ai.txt > /tmp/requirements-ai-no-pins.txt
sed 's/==[0-9].*//g' requirements-remaining.txt > /tmp/requirements-remaining-no-pins.txt

echo "Testing core requirements without pins..."
pip install -r /tmp/requirements-core-no-pins.txt

echo "Testing AI requirements without pins..."
pip install -r /tmp/requirements-ai-no-pins.txt

echo "Testing remaining requirements without pins..."
pip install -r /tmp/requirements-remaining-no-pins.txt

echo "✅ All requirements install successfully without version pins"

# Test 4: Create locked requirements with pip-compile
echo "🧪 TEST 4: Creating locked requirements with pip-compile..."

# Create a single requirements.in file
cat requirements-core.txt requirements-ai.txt requirements-remaining.txt > /tmp/requirements.in

# Remove duplicate lines and clean up
sort /tmp/requirements.in | uniq > /tmp/requirements_clean.in

echo "Compiling locked requirements..."
# CRITICAL: Use python -m piptools to ensure we use the installed version, not old global binary
python -m piptools compile /tmp/requirements_clean.in --output-file /tmp/requirements-locked.txt

echo "✅ Locked requirements created: /tmp/requirements-locked.txt"

# Test 5: Test the locked requirements
echo "🧪 TEST 5: Testing locked requirements..."
pip install -r /tmp/requirements-locked.txt

if pip check; then
    echo "✅ Locked requirements work perfectly"
else
    echo "❌ Locked requirements have issues:"
    pip check
    exit 1
fi

# Test 6: Test Docker build locally
echo "🧪 TEST 6: Testing Docker build locally..."
if docker build -f Dockerfile.deploy -t vernal-agents-test .; then
    echo "✅ Docker build successful"
    docker rmi vernal-agents-test  # Clean up
else
    echo "❌ Docker build failed"
    exit 1
fi

# Cleanup
echo "🧹 Cleaning up..."
deactivate
rm -rf /tmp/dependency_audit
rm -f /tmp/requirements-*-no-pins.txt
rm -f /tmp/requirements.in
rm -f /tmp/requirements_clean.in

echo "🎉 DEPENDENCY AUDIT COMPLETE!"
echo "✅ All requirements install successfully"
echo "✅ No broken dependencies"
echo "✅ Docker build works"
echo "✅ Ready for deployment!"

# Show the locked requirements
echo "📋 LOCKED REQUIREMENTS CREATED:"
echo "You can use /tmp/requirements-locked.txt as your production requirements"
