#!/bin/bash
# generate_env_template.sh - Generate a secure JWT secret and create .env template

set -e

echo "🔐 Generating secure JWT secret and creating .env template..."
echo ""

# Generate a secure random JWT secret (64 characters)
JWT_SECRET=$(openssl rand -base64 48 | tr -d "=+/" | cut -c1-64)

# Create .env template with secure JWT secret
cat > .env.template << EOF
# Database Configuration
DB_HOST=50.6.198.220
DB_USER=vernalcontentum_vernaluse
DB_PASSWORD=[REPLACE_WITH_YOUR_DB_PASSWORD]
DB_NAME=vernalcontentum_contentMachine
DB_PORT=3306

# JWT Authentication
JWT_SECRET_KEY=${JWT_SECRET}

# OpenAI API
OPENAI_API_KEY=[REPLACE_WITH_YOUR_OPENAI_API_KEY]

# Environment
ENVIRONMENT=production
DEBUG=false

# Optional: Email/SMTP Configuration
# MAIL_FROM=noreply@vernalcontentum.com
# MAIL_USERNAME=[YOUR_SMTP_USERNAME]
# MAIL_PASSWORD=[YOUR_SMTP_PASSWORD]
# MAIL_HOST=smtp.gmail.com
# MAIL_PORT=465
EOF

echo "✅ Generated secure JWT secret: ${JWT_SECRET:0:20}..."
echo "✅ Created .env.template file"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env.template and replace [REPLACE_WITH_YOUR_DB_PASSWORD] with your actual database password"
echo "2. Replace [REPLACE_WITH_YOUR_OPENAI_API_KEY] with your OpenAI API key"
echo "3. Copy to production: cp .env.template /home/ubuntu/vernal-agents-post-v0/.env"
echo "4. Set permissions: chmod 600 /home/ubuntu/vernal-agents-post-v0/.env"
echo ""
echo "⚠️  IMPORTANT: The JWT_SECRET_KEY has been generated and is ready to use."
echo "⚠️  If you generate a new one, ALL existing user sessions will be invalidated!"

