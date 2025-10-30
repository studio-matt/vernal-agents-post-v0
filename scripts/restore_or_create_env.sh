#!/bin/bash
# restore_or_create_env.sh - Restore .env from backup or create new one with secure JWT

set -e

ENV_FILE="/home/ubuntu/vernal-agents-post-v0/.env"
BACKUP_FILE="/home/ubuntu/.env.backup"

echo "🔐 .env File Restoration and Creation Script"
echo "============================================"
echo ""

# Check if .env already exists
if [ -f "$ENV_FILE" ]; then
    echo "✅ .env file already exists at: $ENV_FILE"
    echo "📋 Current contents (without secrets):"
    grep -E "^[^=]+=" "$ENV_FILE" | sed 's/=.*/=***/' || true
    echo ""
    read -p "Do you want to keep it or recreate? (keep/recreate) [keep]: " choice
    choice=${choice:-keep}
    if [ "$choice" = "recreate" ]; then
        echo "🔄 Will recreate .env file..."
    else
        echo "✅ Keeping existing .env file"
        exit 0
    fi
fi

# Try to restore from backup
if [ -f "$BACKUP_FILE" ]; then
    echo "🔍 Found backup file at: $BACKUP_FILE"
    echo "📋 Backup file exists, attempting to restore..."
    sudo cp "$BACKUP_FILE" "$ENV_FILE"
    sudo chown ubuntu:ubuntu "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo "✅ Restored .env from backup!"
    echo ""
    echo "📋 Verifying restored file has required values..."
    
    # Check for required variables
    MISSING=()
    for var in DB_HOST DB_USER DB_PASSWORD DB_NAME JWT_SECRET_KEY; do
        if ! grep -q "^${var}=" "$ENV_FILE"; then
            MISSING+=("$var")
        fi
    done
    
    if [ ${#MISSING[@]} -eq 0 ]; then
        echo "✅ All required variables present in restored .env"
        exit 0
    else
        echo "⚠️  Missing variables in backup: ${MISSING[*]}"
        echo "🔄 Will create new .env file..."
    fi
else
    echo "⚠️  No backup file found at: $BACKUP_FILE"
    echo "🔄 Will create new .env file..."
fi

# Generate new JWT secret
echo ""
echo "🔐 Generating secure JWT secret..."
JWT_SECRET=$(openssl rand -base64 48 | tr -d "=+/" | cut -c1-64)
echo "✅ Generated secure JWT secret"

# Prompt for database password
echo ""
echo "📝 Database Configuration"
echo "-----------------------"
echo "DB_HOST: 50.6.198.220"
echo "DB_USER: vernalcontentum_vernaluse"
echo "DB_NAME: vernalcontentum_contentMachine"
echo "DB_PORT: 3306"
echo ""
read -sp "Enter DB_PASSWORD: " DB_PASSWORD
echo ""

# Prompt for OpenAI API key
echo ""
read -sp "Enter OPENAI_API_KEY (or press Enter to skip): " OPENAI_API_KEY
echo ""

# Create .env file
echo ""
echo "📝 Creating .env file..."
cat > "$ENV_FILE" << EOF
# Database Configuration
DB_HOST=50.6.198.220
DB_USER=vernalcontentum_vernaluse
DB_PASSWORD=${DB_PASSWORD}
DB_NAME=vernalcontentum_contentMachine
DB_PORT=3306

# JWT Authentication
JWT_SECRET_KEY=${JWT_SECRET}

# OpenAI API
EOF

if [ -n "$OPENAI_API_KEY" ]; then
    echo "OPENAI_API_KEY=${OPENAI_API_KEY}" >> "$ENV_FILE"
else
    echo "# OPENAI_API_KEY=[ADD_YOUR_KEY_HERE]" >> "$ENV_FILE"
fi

cat >> "$ENV_FILE" << EOF

# Environment
ENVIRONMENT=production
DEBUG=false
EOF

# Set permissions
chmod 600 "$ENV_FILE"
sudo chown ubuntu:ubuntu "$ENV_FILE"

echo "✅ Created .env file at: $ENV_FILE"
echo ""
echo "📋 Summary:"
echo "  - DB_HOST: 50.6.198.220"
echo "  - DB_USER: vernalcontentum_vernaluse"
echo "  - DB_NAME: vernalcontentum_contentMachine"
echo "  - JWT_SECRET_KEY: ${JWT_SECRET:0:20}... (64 chars)"
echo ""
echo "⚠️  IMPORTANT: Generated a NEW JWT_SECRET_KEY"
echo "⚠️  ALL existing user sessions/tokens will be invalidated"
echo "⚠️  Users will need to log in again"
echo ""
echo "🔄 To restart the service:"
echo "   sudo systemctl restart vernal-agents"
echo "   curl -f http://localhost:8000/health"

