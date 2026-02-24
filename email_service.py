"""
Email Service for Authentication
Handles OTP and password reset emails.
Uses MAIL_* from process env, or from Admin Settings (SystemSettings env_MAIL_*) when passed via config_overrides.
"""

import os
import logging
from typing import Optional, Dict, Any
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi_mail.errors import ConnectionErrors
import asyncio

logger = logging.getLogger(__name__)

def _get_mail_value(key: str, config_overrides: Optional[Dict[str, str]] = None, default: str = None) -> Optional[str]:
    """Get MAIL_* value: config_overrides first (Admin Settings), then os.getenv."""
    if config_overrides and config_overrides.get(key):
        return config_overrides[key].strip() or None
    return (os.getenv(key) or "").strip() or (default if default is not None else None)

class EmailService:
    def __init__(self, config_overrides: Optional[Dict[str, str]] = None):
        port_val = _get_mail_value("MAIL_PORT", config_overrides) or "587"
        port = int(port_val)
        use_ssl = port == 465  # SSL for port 465, TLS for port 587

        username = _get_mail_value("MAIL_USERNAME", config_overrides)
        password = _get_mail_value("MAIL_PASSWORD", config_overrides)
        from_addr = _get_mail_value("MAIL_FROM", config_overrides) or "noreply@vernalcontentum.com"
        server = _get_mail_value("MAIL_SERVER", config_overrides) or "smtp.gmail.com"

        self.mail_config = ConnectionConfig(
            MAIL_USERNAME=username,
            MAIL_PASSWORD=password,
            MAIL_FROM=from_addr,
            MAIL_PORT=port,
            MAIL_SERVER=server,
            MAIL_STARTTLS=not use_ssl,  # TLS for port 587
            MAIL_SSL_TLS=use_ssl,       # SSL for port 465
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True
        )
        self.fastmail = FastMail(self.mail_config)
    
    async def send_otp_email(self, email: str, otp_code: str, user_name: str = None) -> bool:
        """Send OTP verification email"""
        try:
            subject = "Verify Your Email - Vernal Contentum"
            verification_url = f"https://machine.vernalcontentum.com/login?email={email}&otp={otp_code}&verify=true"
            body = f"""
            <html>
            <body>
                <h2>Email Verification</h2>
                <p>Hello {user_name or 'User'},</p>
                <p>Your verification code is: <strong>{otp_code}</strong></p>
                <p>This code will expire in 10 minutes.</p>
                <p><strong>Click here to verify your email:</strong></p>
                <p><a href="{verification_url}" style="background-color: #3d545f; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Verify Email</a></p>
                <p>Or copy and paste this link: {verification_url}</p>
                <p>If you didn't request this, please ignore this email.</p>
                <br>
                <p>Best regards,<br>Vernal Contentum Team</p>
            </body>
            </html>
            """
            
            message = MessageSchema(
                subject=subject,
                recipients=[email],
                body=body,
                subtype="html",
                headers={
                    "X-Mailer": "Vernal Contentum Auth System",
                    "X-Priority": "3",
                    "X-MSMail-Priority": "Normal",
                    "Importance": "Normal"
                }
            )
            
            await self.fastmail.send_message(message)
            logger.info(f"OTP email sent successfully to: {email}")
            return True
            
        except ConnectionErrors as e:
            logger.error(f"Email connection error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to send OTP email: {str(e)}")
            return False
    
    async def send_password_reset_email(self, email: str, otp_code: str, user_name: str = None) -> bool:
        """Send password reset OTP email"""
        try:
            subject = "Password Reset - Vernal Contentum"
            reset_url = f"https://machine.vernalcontentum.com/verify-otp?email={email}"
            body = f"""
            <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>Hello {user_name or 'User'},</p>
                <p>You requested to reset your password. Your reset code is: <strong>{otp_code}</strong></p>
                <p>This code will expire in 10 minutes.</p>
                <p><strong>Click here to reset your password:</strong></p>
                <p><a href="{reset_url}" style="background-color: #3d545f; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Reset Password</a></p>
                <p>Or copy and paste this link: {reset_url}</p>
                <p>If you didn't request this, please ignore this email.</p>
                <br>
                <p>Best regards,<br>Vernal Contentum Team</p>
            </body>
            </html>
            """
            
            message = MessageSchema(
                subject=subject,
                recipients=[email],
                body=body,
                subtype="html",
                headers={
                    "X-Mailer": "Vernal Contentum Auth System",
                    "X-Priority": "3",
                    "X-MSMail-Priority": "Normal",
                    "Importance": "Normal"
                }
            )
            
            await self.fastmail.send_message(message)
            logger.info(f"Password reset email sent successfully to: {email}")
            return True
            
        except ConnectionErrors as e:
            logger.error(f"Email connection error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            return False

# Global email service instance (initialized lazily to handle errors)
email_service = None

# Fallback mock email service if real email fails
class MockEmailService:
    async def send_otp_email(self, email: str, otp_code: str, user_name: str = None) -> bool:
        logger.info(f"Mock OTP email sent to: {email}, code: {otp_code}")
        return True
    
    async def send_password_reset_email(self, email: str, otp_code: str, user_name: str = None) -> bool:
        logger.info(f"Mock password reset email sent to: {email}, code: {otp_code}")
        return True

# Use real email service if configured, otherwise mock
# config_overrides: optional dict of MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM, MAIL_SERVER, MAIL_PORT from Admin > Environment Variables
def get_email_service(config_overrides: Optional[Dict[str, str]] = None):
    global email_service

    mail_username = _get_mail_value("MAIL_USERNAME", config_overrides)
    mail_password = _get_mail_value("MAIL_PASSWORD", config_overrides)

    if not mail_username or not mail_password:
        logger.warning("Email credentials not configured (env or Admin Settings), using mock email service")
        return MockEmailService()

    # When overrides provided (Admin Settings), don't use global cache; build fresh so Admin values are used
    if config_overrides:
        try:
            return EmailService(config_overrides=config_overrides)
        except Exception as e:
            logger.error(f"Failed to initialize email service with Admin config: {e}, using mock email service")
            return MockEmailService()

    # No overrides: use process env and cache
    if email_service is None:
        try:
            email_service = EmailService(config_overrides=None)
            logger.info("Email service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize email service: {e}, using mock email service")
            return MockEmailService()

    return email_service
