#!/bin/bash
set -e

echo "🔄 Switching from SFTP to Local Image Storage"
echo "=============================================="
echo ""

BACKEND_DIR="/home/ubuntu/vernal-agents-post-v0"
cd "$BACKEND_DIR"

# Backup
echo "📋 Backing up files..."
BACKUP_SUFFIX=$(date +%Y%m%d_%H%M%S)
cp tools.py "tools.py.backup.$BACKUP_SUFFIX"
cp main.py "main.py.backup.$BACKUP_SUFFIX"
echo "✅ Backups created"
echo ""

# Replace function in tools.py
echo "📋 Updating tools.py..."
python3 << 'PYEOF'
import re

tools_file = "/home/ubuntu/vernal-agents-post-v0/tools.py"
with open(tools_file, 'r') as f:
    content = f.read()

# Replace the entire upload_image_to_sftp function
old_func = r'def upload_image_to_sftp\(image_data: bytes, filename: str\) -> str:.*?return None\n'
new_func = '''def save_image_locally(image_data: bytes, filename: str) -> str:
    """Save image data to local storage and return the permanent URL."""
    try:
        # Get the directory where tools.py is located
        tools_dir = os.path.dirname(os.path.abspath(__file__))
        upload_dir = os.path.join(tools_dir, "uploads", "images")
        
        # Create directory if it doesn't exist
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file locally
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        # Return URL that will be served by FastAPI/nginx
        base_url = f"https://themachine.vernalcontentum.com/images/{filename}"
        
        logger.info(f"✅ Saved image locally: {file_path}")
        logger.info(f"✅ Image URL: {base_url}")
        return base_url
        
    except Exception as e:
        logger.error(f"Failed to save image locally: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None
'''

content = re.sub(old_func, new_func, content, flags=re.DOTALL)
content = content.replace('upload_image_to_sftp(image_data, filename)', 'save_image_locally(image_data, filename)')

with open(tools_file, 'w') as f:
    f.write(content)

print("✅ tools.py updated")
PYEOF

# Add StaticFiles import to main.py
echo "📋 Updating main.py..."
if ! grep -q "from fastapi.staticfiles import StaticFiles" main.py; then
    sed -i '/from fastapi.responses import JSONResponse/a from fastapi.staticfiles import StaticFiles' main.py
fi

# Add static file mounting
if ! grep -q 'app.mount("/images"' main.py; then
    MOUNT_CODE='# Mount static files directory for images\nuploads_dir = os.path.join(os.path.dirname(__file__), "uploads", "images")\nos.makedirs(uploads_dir, exist_ok=True)\napp.mount("/images", StaticFiles(directory=uploads_dir), name="images")\nlogger.info(f"✅ Static file serving enabled for images: {uploads_dir}")'
    sed -i '/# --- ROUTER INCLUDES MUST BE HERE ---/i '"$MOUNT_CODE" main.py
fi

# Create directory
echo "📋 Creating uploads/images directory..."
mkdir -p uploads/images
chmod 755 uploads/images

# Test syntax
echo "📋 Testing syntax..."
source venv/bin/activate
python3 -m py_compile tools.py && echo "✅ tools.py OK" || { echo "❌ tools.py error"; exit 1; }
python3 -m py_compile main.py && echo "✅ main.py OK" || { echo "❌ main.py error"; exit 1; }

# Restart
echo "📋 Restarting service..."
sudo systemctl restart vernal-agents
sleep 3
sudo systemctl status vernal-agents --no-pager -l | head -10

echo ""
echo "✅ DONE! Images will now save locally to: $BACKEND_DIR/uploads/images/"
echo "   Accessible at: https://themachine.vernalcontentum.com/images/{filename}"
