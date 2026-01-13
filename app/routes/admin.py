"""
Admin endpoints extracted from main.py
Moved from main.py to preserve API contract parity
"""
import logging
import json
import os
import secrets
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from auth_api import get_admin_user, get_plugin_user
from database import SessionLocal
from app.schemas.models import TransferCampaignRequest
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

admin_router = APIRouter()

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@admin_router.get("/admin/settings/{setting_key}")
def get_system_setting(setting_key: str, admin_user = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Get a system setting by key - ADMIN ONLY"""
    try:
        from models import SystemSettings
        setting = db.query(SystemSettings).filter(SystemSettings.setting_key == setting_key).first()
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting '{setting_key}' not found"
            )
        return {
            "status": "success",
            "setting_key": setting.setting_key,
            "setting_value": setting.setting_value,
            "description": setting.description,
            "updated_at": setting.updated_at.isoformat() if setting.updated_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching system setting: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch setting: {str(e)}"
        )

# Admin User Management endpoints
@admin_router.get("/admin/users")
def get_all_users(admin_user = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Get all users with admin status - ADMIN ONLY"""
    try:
        from models import User
        users = db.query(User).all()
        return {
            "status": "success",
            "users": [
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_admin": getattr(user, 'is_admin', False),
                    "is_verified": getattr(user, 'is_verified', False),
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }
                for user in users
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users: {str(e)}"
        )

@admin_router.get("/admin/env-check")
def check_environment_variables(admin_user = Depends(get_admin_user)):
    """
    Check which environment variables are set and which are missing - ADMIN ONLY
    Returns a comprehensive report of all environment variables used by the system.
    """
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    # Define all environment variables used by the system
    env_vars = {
        # Critical - Required for app to function
        "critical": {
            "DB_HOST": {
                "description": "Database host address",
                "required": True,
                "example": "50.6.198.220"
            },
            "DB_USER": {
                "description": "Database username",
                "required": True,
                "example": "vernalcontentum_vernaluse"
            },
            "DB_PASSWORD": {
                "description": "Database password",
                "required": True,
                "example": "your_password"
            },
            "DB_NAME": {
                "description": "Database name",
                "required": True,
                "example": "vernalcontentum_contentMachine"
            },
            "JWT_SECRET_KEY": {
                "description": "JWT secret key for authentication",
                "required": True,
                "example": "your-secret-key-please-change-in-production"
            },
            "JWT_ALGORITHM": {
                "description": "JWT algorithm (usually HS256)",
                "required": False,
                "default": "HS256"
            },
        },
        # API Keys - Some may be optional depending on features used
        "api_keys": {
            "OPENAI_API_KEY": {
                "description": "OpenAI API key (can also be set in Admin Settings as global key)",
                "required": False,
                "note": "Can be set globally in Admin Settings > System > Platform Keys"
            },
            "AIRTABLE_API_TOKEN": {
                "description": "Airtable API token",
                "required": False,
                "note": "Only needed if using Airtable integration"
            },
            "BASE_ID": {
                "description": "Airtable base ID",
                "required": False,
                "note": "Only needed if using Airtable integration"
            },
            "TABLE_NAME": {
                "description": "Airtable table name",
                "required": False,
                "note": "Only needed if using Airtable integration"
            },
        },
        # SFTP Configuration
        "sftp": {
            "SFTP_HOST": {
                "description": "SFTP server hostname",
                "required": False,
                "note": "Only needed if using SFTP file uploads"
            },
            "SFTP_USER": {
                "description": "SFTP username",
                "required": False,
                "note": "Only needed if using SFTP file uploads"
            },
            "SFTP_PASS": {
                "description": "SFTP password",
                "required": False,
                "note": "Only needed if using SFTP file uploads"
            },
            "SFTP_PORT": {
                "description": "SFTP port (default: 22)",
                "required": False,
                "default": "22"
            },
            "SFTP_REMOTE_DIR": {
                "description": "SFTP remote directory path",
                "required": False,
                "default": "/home/{SFTP_USER}/public_html"
            },
        },
        # Email Configuration
        "email": {
            "MAIL_USERNAME": {
                "description": "Email username for SMTP",
                "required": False,
                "note": "Only needed if using email features"
            },
            "MAIL_PASSWORD": {
                "description": "Email password for SMTP",
                "required": False,
                "note": "Only needed if using email features"
            },
            "MAIL_FROM": {
                "description": "From email address",
                "required": False,
                "note": "Only needed if using email features"
            },
            "MAIL_SERVER": {
                "description": "SMTP server address",
                "required": False,
                "default": "smtp.gmail.com"
            },
            "MAIL_PORT": {
                "description": "SMTP port",
                "required": False,
                "default": "465"
            },
        },
        # Social Platform OAuth (can also be set in Admin Settings)
        "oauth": {
            "LINKEDIN_CLIENT_ID": {
                "description": "LinkedIn OAuth client ID",
                "required": False,
                "note": "Can be set in Admin Settings > System > Platform Keys"
            },
            "LINKEDIN_CLIENT_SECRET": {
                "description": "LinkedIn OAuth client secret",
                "required": False,
                "note": "Can be set in Admin Settings > System > Platform Keys"
            },
            "LINKEDIN_REDIRECT_URI": {
                "description": "LinkedIn OAuth redirect URI",
                "required": False,
                "default": "https://themachine.vernalcontentum.com/linkedin/callback"
            },
            "TWITTER_API_KEY": {
                "description": "Twitter OAuth API key",
                "required": False,
                "note": "Can be set in Admin Settings > System > Platform Keys"
            },
            "TWITTER_API_SECRET": {
                "description": "Twitter OAuth API secret",
                "required": False,
                "note": "Can be set in Admin Settings > System > Platform Keys"
            },
            "TWITTER_CALLBACK_URL": {
                "description": "Twitter OAuth callback URL",
                "required": False,
                "default": "https://machine.vernalcontentum.com/twitter/callback"
            },
            "FACEBOOK_APP_ID": {
                "description": "Facebook OAuth app ID",
                "required": False,
                "note": "Can be set in Admin Settings > System > Platform Keys"
            },
            "FACEBOOK_APP_SECRET": {
                "description": "Facebook OAuth app secret",
                "required": False,
                "note": "Can be set in Admin Settings > System > Platform Keys"
            },
            "FACEBOOK_REDIRECT_URI": {
                "description": "Facebook OAuth redirect URI",
                "required": False,
                "default": "https://machine.vernalcontentum.com/facebook/callback"
            },
            "INSTAGRAM_REDIRECT_URI": {
                "description": "Instagram OAuth redirect URI",
                "required": False,
                "default": "https://machine.vernalcontentum.com/instagram/callback"
            },
        },
        # Guardrails Configuration
        "guardrails": {
            "GUARDRAILS_BLOCK_INJECTION": {
                "description": "Enable prompt injection blocking (0=warn only, 1=block)",
                "required": False,
                "default": "0"
            },
        },
        # Code Health Configuration
        "code_health": {
            "CODE_HEALTH_LOC_THRESHOLD": {
                "description": "Maximum lines of code per file threshold",
                "required": False,
                "default": "3000"
            },
            "CODE_HEALTH_ENABLE_PYLINT": {
                "description": "Enable pylint analysis (0=disabled, 1=enabled)",
                "required": False,
                "default": "0"
            },
            "CODE_HEALTH_PYLINT_TARGETS": {
                "description": "Comma-separated list of files/dirs for pylint",
                "required": False,
                "default": ""
            },
        },
        # Gas Meter Configuration (Future)
        "gas_meter": {
            "EC2_INSTANCE_TYPE": {
                "description": "EC2 instance type for display",
                "required": False,
                "default": ""
            },
            "EC2_HOURLY_RATE_USD": {
                "description": "EC2 hourly cost in USD",
                "required": False,
                "default": ""
            },
            "EC2_UTILIZATION_FACTOR": {
                "description": "EC2 utilization factor (0.0-1.0)",
                "required": False,
                "default": "1.0"
            },
        },
        # Optional/Misc
        "optional": {
            "GITHUB_SHA": {
                "description": "Git commit SHA for version display",
                "required": False,
                "note": "Automatically set by CI/CD"
            },
        },
    }
    
    # Check each variable
    results = {
        "critical": [],
        "api_keys": [],
        "sftp": [],
        "email": [],
        "oauth": [],
        "guardrails": [],
        "code_health": [],
        "gas_meter": [],
        "optional": [],
    }
    
    missing_critical = []
    
    for category, vars_dict in env_vars.items():
        for var_name, var_info in vars_dict.items():
            value = os.getenv(var_name)
            is_set = value is not None and value.strip() != ""
            
            result = {
                "name": var_name,
                "description": var_info.get("description", ""),
                "is_set": is_set,
                "has_value": is_set and len(value) > 0,
                "required": var_info.get("required", False),
                "default": var_info.get("default", None),
                "note": var_info.get("note", None),
            }
            
            # Mask sensitive values
            if is_set and var_info.get("required", False):
                if "PASSWORD" in var_name or "SECRET" in var_name or "KEY" in var_name or "TOKEN" in var_name:
                    result["value_preview"] = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
                else:
                    result["value_preview"] = value[:50] if len(value) > 50 else value
            elif is_set:
                result["value_preview"] = "Set (hidden)" if "PASSWORD" in var_name or "SECRET" in var_name or "KEY" in var_name or "TOKEN" in var_name else value[:50]
            else:
                result["value_preview"] = None
            
            results[category].append(result)
            
            if var_info.get("required", False) and not is_set:
                missing_critical.append(var_name)
    
    # Summary
    total_vars = sum(len(vars_dict) for vars_dict in env_vars.values())
    set_vars = sum(1 for category_results in results.values() for r in category_results if r["is_set"])
    missing_required = len(missing_critical)
    
    return {
        "status": "success",
        "summary": {
            "total_variables": total_vars,
            "set_variables": set_vars,
            "missing_variables": total_vars - set_vars,
            "missing_critical": missing_required,
            "all_critical_set": missing_required == 0,
        },
        "missing_critical": missing_critical,
        "variables": results,
        "recommendations": [
            "Set all critical variables for the app to function properly",
            "Set OPENAI_API_KEY or configure global key in Admin Settings > System > Platform Keys",
            "Set OAuth credentials in Admin Settings if using social platform integrations",
            "Set SFTP credentials if using file upload features",
            "Set email credentials if using email features",
        ] if missing_required > 0 else [
            "All critical variables are set! ✅",
            "Optional variables can be configured as needed for additional features",
        ],
    }

@admin_router.post("/admin/env-update")
def update_environment_variable(key: str, value: str, admin_user = Depends(get_admin_user), db: Session = Depends(get_db)):
    """
    Update an environment variable value in system_settings - ADMIN ONLY
    Note: This stores the value in system_settings. For production, you may also need to update systemd environment variables.
    """
    try:
        from models import SystemSettings
        
        # List of editable environment variables (for safety - only allow specific vars)
        editable_vars = [
            "GUARDRAILS_BLOCK_INJECTION",
            "CODE_HEALTH_LOC_THRESHOLD",
            "CODE_HEALTH_ENABLE_PYLINT",
            "CODE_HEALTH_PYLINT_TARGETS",
            "EC2_INSTANCE_TYPE",
            "EC2_HOURLY_RATE_USD",
            "EC2_UTILIZATION_FACTOR",
            "MAIL_USERNAME",
            "MAIL_PASSWORD",
            "MAIL_FROM",
            "MAIL_SERVER",
            "MAIL_PORT",
        ]
        
        if key not in editable_vars:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Variable {key} is not editable via this endpoint"
            )
        
        # Store in system_settings with prefix "env_" to distinguish from other settings
        setting_key = f"env_{key}"
        existing = db.query(SystemSettings).filter(SystemSettings.setting_key == setting_key).first()
        
        if existing:
            existing.setting_value = value
            existing.updated_at = datetime.now()
        else:
            new_setting = SystemSettings(
                setting_key=setting_key,
                setting_value=value,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(new_setting)
        
        db.commit()
        
        logger.info(f"✅ Admin {admin_user.id} updated environment variable {key} in system_settings")
        
        return {
            "status": "success",
            "message": f"Environment variable {key} updated successfully",
            "key": key,
            "value": value if "PASSWORD" not in key and "SECRET" not in key and "KEY" not in key else "***"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating environment variable: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update environment variable: {str(e)}"
        )

# MOVED TO: app/schemas/models.py (TransferCampaignRequest)

@admin_router.post("/admin/campaigns/{campaign_id}/transfer")
def transfer_campaign(campaign_id: str, request: TransferCampaignRequest, admin_user = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Transfer a campaign to another user - ADMIN ONLY"""
    try:
        from models import Campaign, User
        
        target_user_id = request.target_user_id
        
        # Verify target user exists
        target_user = db.query(User).filter(User.id == target_user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target user {target_user_id} not found"
            )
        
        # Get campaign (admin can see all campaigns)
        campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign {campaign_id} not found"
            )
        
        # Store original user for logging
        original_user_id = campaign.user_id
        
        # Transfer campaign
        campaign.user_id = target_user_id
        campaign.updated_at = datetime.now()
        db.commit()
        db.refresh(campaign)
        
        logger.info(f"✅ Admin {admin_user.id} transferred campaign {campaign_id} from user {original_user_id} to user {target_user_id}")
        
        return {
            "status": "success",
            "message": f"Campaign transferred to {target_user.username} ({target_user.email})",
            "campaign": {
                "campaign_id": campaign.campaign_id,
                "campaign_name": campaign.campaign_name,
                "user_id": campaign.user_id,
                "original_user_id": original_user_id,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transferring campaign: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transfer campaign: {str(e)}"
        )

@admin_router.post("/admin/users/{user_id}/admin")
def grant_admin_access(user_id: int, admin_user = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Grant admin access to a user - ADMIN ONLY"""
    try:
        from models import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Prevent removing your own admin access
        if user.id == admin_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify your own admin status"
            )
        
        user.is_admin = True
        db.commit()
        db.refresh(user)
        logger.info(f"✅ Granted admin access to user {user_id} ({user.email})")
        
        return {
            "status": "success",
            "message": f"Admin access granted to {user.email}",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": True
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error granting admin access: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to grant admin access: {str(e)}"
        )

@admin_router.delete("/admin/users/{user_id}/admin")
def revoke_admin_access(user_id: int, admin_user = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Revoke admin access from a user - ADMIN ONLY"""
    try:
        from models import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # Prevent removing your own admin access
        if user.id == admin_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify your own admin status"
            )
        
        user.is_admin = False
        db.commit()
        db.refresh(user)
        logger.info(f"✅ Revoked admin access from user {user_id} ({user.email})")
        
        return {
            "status": "success",
            "message": f"Admin access revoked from {user.email}",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": False
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking admin access: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke admin access: {str(e)}"
        )

# Code Health Scanner endpoints
@admin_router.get("/admin/code-health")
def get_code_health(admin_user = Depends(get_admin_user)):
    """Get latest code health scan results - ADMIN ONLY"""
    try:
        import json
        from pathlib import Path
        
        reports_dir = Path("reports")
        json_path = reports_dir / "code_health.json"
        
        if not json_path.exists():
            return {
                "status": "no_scan",
                "message": "No scan results found. Run a scan first.",
                "violations": [],
                "violation_count": 0,
            }
        
        with open(json_path, 'r', encoding='utf-8') as f:
            scan_data = json.load(f)
        
        return {
            "status": "success",
            **scan_data
        }
    except Exception as e:
        logger.error(f"Error fetching code health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch code health: {str(e)}"
        )

@admin_router.post("/admin/code-health/scan")
def trigger_code_health_scan(admin_user = Depends(get_admin_user)):
    """Trigger a new code health scan - ADMIN ONLY"""
    try:
        from code_health.scanner import scan_codebase, generate_reports
        import os
        
        # Get root directory (backend repo root)
        root_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Run scan
        logger.info(f"🔍 Starting code health scan in {root_dir}")
        scan_results = scan_codebase(root_dir=root_dir)
        
        # Generate reports
        report_paths = generate_reports(scan_results)
        
        logger.info(f"✅ Code health scan complete: {scan_results['violation_count']} violations found")
        
        return {
            "status": "success",
            "message": "Scan completed successfully",
            "scan_results": scan_results,
            "reports": report_paths,
        }
    except Exception as e:
        logger.error(f"Error running code health scan: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run code health scan: {str(e)}"
        )

@admin_router.post("/admin/plugins/api-keys")
def create_plugin_api_key(
    name: Optional[str] = None,
    admin_user = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Generate a new API key for WordPress plugin authentication - ADMIN ONLY"""
    try:
        from models import PluginAPIKey
        import secrets
        from datetime import datetime, timedelta
        
        # Generate secure API key (64 character hex string)
        api_key = f"vcb_{secrets.token_hex(32)}"  # vcb = vernal contentum backend
        
        # Create API key record
        plugin_key = PluginAPIKey(
            user_id=admin_user.id,
            api_key=api_key,
            name=name or f"Plugin API Key {datetime.utcnow().strftime('%Y-%m-%d')}",
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(plugin_key)
        db.commit()
        db.refresh(plugin_key)
        
        logger.info(f"✅ Created plugin API key for user {admin_user.id}: {plugin_key.id}")
        
        return {
            "status": "success",
            "message": "API key created successfully",
            "data": {
                "id": plugin_key.id,
                "api_key": api_key,  # Only returned once - user must save it
                "name": plugin_key.name,
                "created_at": plugin_key.created_at.isoformat(),
                "user_id": plugin_key.user_id
            }
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating plugin API key: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}"
        )

@admin_router.get("/admin/plugins/api-keys")
def list_plugin_api_keys(
    admin_user = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List all plugin API keys for the admin user - ADMIN ONLY"""
    try:
        from models import PluginAPIKey
        
        # Get all API keys for this user
        api_keys = db.query(PluginAPIKey).filter(
            PluginAPIKey.user_id == admin_user.id
        ).order_by(PluginAPIKey.created_at.desc()).all()
        
        return {
            "status": "success",
            "data": [
                {
                    "id": key.id,
                    "name": key.name,
                    "is_active": key.is_active,
                    "created_at": key.created_at.isoformat() if key.created_at else None,
                    "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                    "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                    # Don't return full API key for security - only show first/last few chars
                    "api_key_preview": f"{key.api_key[:8]}...{key.api_key[-4:]}" if len(key.api_key) > 12 else "***"
                }
                for key in api_keys
            ]
        }
    except Exception as e:
        logger.error(f"Error listing plugin API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list API keys: {str(e)}"
        )

@admin_router.delete("/admin/plugins/api-keys/{key_id}")
def delete_plugin_api_key(
    key_id: int,
    admin_user = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Delete or deactivate a plugin API key - ADMIN ONLY"""
    try:
        from models import PluginAPIKey
        
        api_key = db.query(PluginAPIKey).filter(
            PluginAPIKey.id == key_id,
            PluginAPIKey.user_id == admin_user.id  # Only allow deleting own keys
        ).first()
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        # Soft delete - mark as inactive
        api_key.is_active = False
        db.commit()
        
        logger.info(f"✅ Deactivated plugin API key {key_id} for user {admin_user.id}")
        
        return {
            "status": "success",
            "message": "API key deactivated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting plugin API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete API key: {str(e)}"
        )

@admin_router.get("/plugin/test")
def plugin_test_endpoint(plugin_user = Depends(get_plugin_user)):
    """Test endpoint for WordPress plugin authentication - Requires API key"""
    return {
        "status": "success",
        "message": "Plugin authentication successful",
        "user": {
            "id": plugin_user.id,
            "username": plugin_user.username,
            "email": plugin_user.email
        }
    }

@admin_router.put("/admin/settings/{setting_key}")
def update_system_setting(setting_key: str, setting_data: Dict[str, Any], admin_user = Depends(get_admin_user), db: Session = Depends(get_db)):
    """Update or create a system setting - ADMIN ONLY"""
    try:
        from models import SystemSettings
        setting = db.query(SystemSettings).filter(SystemSettings.setting_key == setting_key).first()
        
        if setting:
            # Update existing setting
            if "setting_value" in setting_data:
                setting.setting_value = setting_data["setting_value"]
            if "description" in setting_data:
                setting.description = setting_data["description"]
            setting.updated_at = datetime.now()
            db.commit()
            db.refresh(setting)
            logger.info(f"✅ Updated system setting: {setting_key}")
            
            # Clear cache if this is the topic extraction prompt
            if setting_key == "topic_extraction_prompt":
                try:
                    from text_processing import clear_topic_prompt_cache
                    clear_topic_prompt_cache()
                except Exception as cache_err:
                    logger.warning(f"⚠️ Failed to clear prompt cache: {cache_err}")
        else:
            # Create new setting
            setting = SystemSettings(
                setting_key=setting_key,
                setting_value=setting_data.get("setting_value", ""),
                description=setting_data.get("description")
            )
            db.add(setting)
            db.commit()
            db.refresh(setting)
            logger.info(f"✅ Created new system setting: {setting_key}")
        
        return {
            "status": "success",
            "message": f"Setting '{setting_key}' updated successfully",
            "setting_key": setting.setting_key,
            "setting_value": setting.setting_value,
            "description": setting.description,
            "updated_at": setting.updated_at.isoformat() if setting.updated_at else None
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating system setting: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update setting: {str(e)}"
        )
@admin_router.get("/plugin/test")
def plugin_test_endpoint(plugin_user = Depends(get_plugin_user)):
    """Test endpoint for WordPress plugin authentication - Requires API key"""
    return {
        "status": "success",
        "message": "Plugin authentication successful",
        "user": {
            "id": plugin_user.id,
            "username": plugin_user.username,
            "email": plugin_user.email
        }
    }
@admin_router.post("/admin/initialize-research-agent-prompts")
def initialize_research_agent_prompts(admin_user = Depends(get_admin_user), db: Session = Depends(get_db)):
    """
    Initialize default research agent prompts in the database if they don't exist.
    This ensures all research agent prompts have default values.
    """
    try:
        from models import SystemSettings
        
        default_prompts = {
            "research_agent_keyword_prompt": """Analyze the following keyword data from a content campaign scrape:

{context}

Based on this data, provide:
- A summary of what the word cloud analysis reveals about the campaign's focus
- Areas where content could be expanded for better balance
- Specific recommendations for improving keyword coverage
- Actionable insights about underrepresented topics

IMPORTANT: Format your response as plain text recommendations without titles, numbering, or markdown headers. Each recommendation should be a clear, actionable insight. Do not include "Recommendations:" or numbered lists (1., 2., etc.). Just provide the insights directly.""",
            
            "research_agent_micro-sentiment_prompt": """Analyze the sentiment data from a content campaign scrape:

{context}

Based on this data, provide:
- Overall sentiment assessment
- Sentiment breakdown by topic/theme
- Areas with lower positive sentiment that need attention
- Recommendations for improving sentiment in specific areas

IMPORTANT: Format your response as plain text recommendations without titles, numbering, or markdown headers. Each recommendation should be a clear, actionable insight. Do not include "Recommendations:" or numbered lists (1., 2., etc.). Just provide the insights directly.""",
            
            "research_agent_topical-map_prompt": """Analyze the topical map data from a content campaign scrape:

{context}

Based on this data, provide topic insights and recommendations.

OUTPUT FORMAT (CRITICAL):
- Output one item per line
- Each line must start with "REC: " (no quotes, include the colon and space)
- No headings like "Main Topics Identified" or "Recommendations:"
- One idea per line
- Each recommendation should be a clear, actionable insight

Example format:
REC: Psilocybin for treatment-resistant depression
REC: Clinical trial content emphasizes short-term outcomes more than long-term effects
REC: Long-term psychological effects of repeated psilocybin therapy
REC: Write an article focused on long-term effects of psilocybin therapy

Do not include:
- Numbered lists (1., 2., etc.)
- Bullet points (-, •, *)
- Markdown headers (###, ##, #)
- Category headers
- Explanatory text between items

Just provide the REC: lines directly.""",
            
            "research_agent_knowledge-graph_prompt": """Analyze the knowledge graph data from a content campaign scrape:

{context}

Based on this data, provide:
- Assessment of entity relationships and structure
- Analysis of connection strengths between concepts
- Identification of weakly connected areas
- Recommendations for strengthening relationships in the knowledge graph

IMPORTANT: Format your response as plain text recommendations without titles, numbering, or markdown headers. Each recommendation should be a clear, actionable insight. Do not include "Recommendations:" or numbered lists (1., 2., etc.). Just provide the insights directly.""",
            
            "research_agent_hashtag-generator_prompt": """Analyze the hashtag data from a content campaign scrape:

{context}

Based on this data, provide:
- Assessment of hashtag mix (industry-standard, trending, niche, campaign-specific)
- Analysis of hashtag performance potential
- Recommendations for optimal hashtag combinations
- Suggested hashtag strategies for different platforms

IMPORTANT: Format your response as plain text recommendations without titles, numbering, or markdown headers. Each recommendation should be a clear, actionable insight. Do not include "Recommendations:" or numbered lists (1., 2., etc.). Just provide the insights directly.""",
            
            "research_agent_idea-generator_prompt": """You are an expert in idea generation. Given the following topics and scraped posts, generate exactly {num_ideas} creative, one-line ideas that are meaningful, actionable, and relevant to the provided topics and posts.

CRITICAL INSTRUCTIONS:
- Focus STRICTLY on the topics provided in the "Topics:" section below
- Each idea must directly relate to these specific topics
- If recommendations or insights are provided, extract the actual topics/keywords from them and use those for idea generation
- Each idea should be a concise, complete sentence or phrase (e.g., "Create a comprehensive guide on pug health issues")
- Avoid vague or incomplete ideas
- Do not include explanations or additional text
- Return ONLY a JSON array of strings, with no markdown formatting, no numbering, no titles

Example output:
["Create a comprehensive guide on pug health issues", "Develop practical tips for pug grooming and care", "Explore pug personality traits and socialization"]

Context:
{context}""",
        }
        
        # Add keyword expansion prompt
        default_prompts["keyword_expansion_prompt"] = """Expand this abbreviation to its full form. Return ONLY the expansion, nothing else. If it's not an abbreviation, return the original word.

Examples:
- WW2 → World War 2
- AI → artificial intelligence
- CEO → Chief Executive Officer
- NASA → National Aeronautics and Space Administration

Abbreviation: {keyword}

Expansion:"""
        
        initialized = []
        for setting_key, prompt_value in default_prompts.items():
            # Check if setting exists
            existing = db.query(SystemSettings).filter(SystemSettings.setting_key == setting_key).first()
            if not existing:
                # Create new setting
                if setting_key == "keyword_expansion_prompt":
                    description = "Prompt for LLM-based keyword abbreviation expansion"
                else:
                    agent_type = setting_key.replace("research_agent_", "").replace("_prompt", "")
                    agent_labels = {
                        "keyword": "Keyword Research Agent",
                        "micro-sentiment": "Micro Sentiment Agent",
                        "topical-map": "Topical Map Agent",
                        "knowledge-graph": "Knowledge Graph Agent",
                        "hashtag-generator": "Hashtag Generator Agent",
                        "idea-generator": "Idea Generator Agent",
                    }
                    description = f"Default prompt for {agent_labels.get(agent_type, agent_type)}"
                
                new_setting = SystemSettings(
                    setting_key=setting_key,
                    setting_value=prompt_value,
                    description=description
                )
                db.add(new_setting)
                initialized.append(setting_key)
                logger.info(f"✅ Initialized {setting_key}")
        
        if initialized:
            db.commit()
            return {
                "status": "success",
                "message": f"Initialized {len(initialized)} prompts",
                "initialized": initialized
            }
        else:
            return {
                "status": "success",
                "message": "All prompts already exist",
                "initialized": []
            }
            
    except Exception as e:
        logger.error(f"Error initializing research agent prompts: {e}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
        return {"status": "error", "message": str(e)}
