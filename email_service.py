"""
Email Service for Authentication
Handles OTP and password reset emails
"""

import os
import logging
from typing import Optional
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi_mail.errors import ConnectionErrors
import asyncio

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.mail_config = ConnectionConfig(
            MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
            MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
            MAIL_FROM=os.getenv("MAIL_FROM", "noreply@vernalcontentum.com"),
            MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
            MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True
        )
        self.fastmail = FastMail(self.mail_config)
    
    async def send_otp_email(self, email: str, otp_code: str, user_name: str = None) -> bool:
        """Send OTP verification email"""
        try:
            subject = "Verify Your Email - Vernal Contentum"
            body = f"""
            <html>
            <body>
                <h2>Email Verification</h2>
                <p>Hello {user_name or 'User'},</p>
                <p>Your verification code is: <strong>{otp_code}</strong></p>
                <p>This code will expire in 10 minutes.</p>
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
                subtype="html"
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
            body = f"""
            <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>Hello {user_name or 'User'},</p>
                <p>You requested to reset your password. Your reset code is: <strong>{otp_code}</strong></p>
                <p>This code will expire in 10 minutes.</p>
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
                subtype="html"
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

# Global email service instance
email_service = EmailService()

# Fallback mock email service if real email fails
class MockEmailService:
    async def send_otp_email(self, email: str, otp_code: str, user_name: str = None) -> bool:
        logger.info(f"Mock OTP email sent to: {email}, code: {otp_code}")
        return True
    
    async def send_password_reset_email(self, email: str, otp_code: str, user_name: str = None) -> bool:
        logger.info(f"Mock password reset email sent to: {email}, code: {otp_code}")
        return True

# Use real email service if configured, otherwise mock
def get_email_service():
    if os.getenv("MAIL_USERNAME") and os.getenv("MAIL_PASSWORD"):
        return email_service
    else:
        logger.warning("Email credentials not configured, using mock email service")
        return MockEmailService()
