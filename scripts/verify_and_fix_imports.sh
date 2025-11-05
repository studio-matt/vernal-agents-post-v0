#!/bin/bash
# Script to verify all critical imports work and fix missing dependencies
# Run this after deployment to ensure all packages are installed

set -e

echo "🔍 Verifying critical imports..."
echo ""

cd /home/ubuntu/vernal-agents-post-v0 || exit 1

# Activate venv
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    exit 1
fi

source venv/bin/activate

# Run the Python import verification
python3 << 'EOF'
import sys

critical_imports = [
    ('sklearn', 'scikit-learn'),
    ('langchain_openai', 'langchain-openai'),
    ('nltk', 'nltk'),
    ('gensim', 'gensim'),
    ('bertopic', 'bertopic'),
    ('numpy', 'numpy'),
    ('fastapi', 'fastapi'),
    ('uvicorn', 'uvicorn'),
    ('sqlalchemy', 'sqlalchemy'),
    ('pymysql', 'pymysql'),
    ('openai', 'openai'),
    ('crewai', 'crewai'),
    ('playwright', 'playwright'),
    ('bs4', 'beautifulsoup4'),
    ('ddgs', 'ddgs'),
    ('pydantic', 'pydantic'),
    ('dotenv', 'python-dotenv'),
    ('langdetect', 'langdetect'),
]

missing = []
for import_name, package_name in critical_imports:
    try:
        __import__(import_name)
        print(f"✅ {package_name} ({import_name})")
    except ImportError:
        missing.append(package_name)
        print(f"❌ {package_name} ({import_name}) - MISSING")

if missing:
    print(f"\n❌ {len(missing)} packages are missing:")
    for pkg in missing:
        print(f"   - {pkg}")
    print("\n📦 Installing missing packages...")
    sys.exit(1)
else:
    print("\n✅ All critical imports verified!")
    sys.exit(0)
EOF

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "📦 Installing missing packages from requirements.txt..."
    pip install -r requirements.txt --no-cache-dir
    
    echo ""
    echo "🔍 Re-verifying imports..."
    source venv/bin/activate
    python3 << 'EOF'
import sys
import subprocess

critical_imports = [
    ('sklearn', 'scikit-learn'),
    ('langchain_openai', 'langchain-openai'),
    ('nltk', 'nltk'),
    ('gensim', 'gensim'),
    ('bertopic', 'bertopic'),
    ('numpy', 'numpy'),
]

missing = []
for import_name, package_name in critical_imports:
    try:
        __import__(import_name)
        print(f"✅ {package_name} ({import_name})")
    except ImportError:
        missing.append(package_name)
        print(f"❌ {package_name} ({import_name}) - STILL MISSING")

if missing:
    print(f"\n❌ {len(missing)} packages still missing after install!")
    print("Manual installation required:")
    for pkg in missing:
        print(f"   pip install {pkg}")
    sys.exit(1)
else:
    print("\n✅ All imports verified after fix!")
    sys.exit(0)
EOF
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ All dependencies fixed! Restarting service..."
        sudo systemctl restart vernal-agents
        sleep 3
        curl -s http://127.0.0.1:8000/health | jq .
    fi
fi

