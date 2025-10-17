"""
Ultra Minimal Authentication API (No External Dependencies)
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Create router
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

# In-memory storage
users_db = {}

# Pydantic models
class UserSignup(BaseModel):
    username: str
    email: str
    password: str
    contact: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    contact: Optional[str]
    is_verified: bool

class LoginResponse(BaseModel):
    status: str
    token: str
    user: UserResponse

class SignupResponse(BaseModel):
    status: str
    message: str
    user: Optional[UserResponse] = None

# Authentication endpoints
@auth_router.post("/signup", response_model=SignupResponse)
async def signup_user(user_data: UserSignup):
    """Register a new user"""
    try:
        logger.info(f"Signup attempt for username: {user_data.username}")
        logger.info(f"Password length: {len(user_data.password)}")
        logger.info(f"Password value: {user_data.password}")
        
        # Check if user already exists
        for user in users_db.values():
            if user["username"] == user_data.username or user["email"] == user_data.email:
                if user["username"] == user_data.username:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username already exists"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already exists"
                    )
        
        # Create new user
        user_id = len(users_db) + 1
        new_user = {
            "id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "password": user_data.password,  # Store plain text for now
            "contact": user_data.contact,
            "is_verified": False
        }
        
        users_db[user_id] = new_user
        
        logger.info(f"User created successfully: {user_id}")
        
        return SignupResponse(
            status="success",
            message="Account created successfully! You can now log in.",
            user=UserResponse(
                id=new_user["id"],
                username=new_user["username"],
                email=new_user["email"],
                contact=new_user["contact"],
                is_verified=new_user["is_verified"]
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Signup failed. Please try again."
        )

@auth_router.post("/login", response_model=LoginResponse)
async def login_user(user_data: UserLogin):
    """Authenticate user and return token"""
    try:
        logger.info(f"Login attempt for username: {user_data.username}")
        
        # Find user by username or email
        user = None
        for u in users_db.values():
            if u["username"] == user_data.username or u["email"] == user_data.username:
                user = u
                break
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Verify password (simple comparison for now)
        if user_data.password != user["password"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Create simple token
        token = f"token-{user['id']}-{user['username']}"
        
        logger.info(f"User logged in successfully: {user['id']}")
        
        return LoginResponse(
            status="success",
            token=token,
            user=UserResponse(
                id=user["id"],
                username=user["username"],
                email=user["email"],
                contact=user["contact"],
                is_verified=user["is_verified"]
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )

@auth_router.post("/verify-email")
async def verify_email(request: dict):
    """Verify user email with OTP (mock implementation)"""
    try:
        email = request.get("email")
        otp_code = request.get("otp_code")
        
        logger.info(f"Email verification attempt for: {email}")
        
        # Find user by email
        user = None
        for u in users_db.values():
            if u["email"] == email:
                user = u
                break
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify OTP code
        if "otp" not in user or user["otp"] != otp_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP code"
            )
        
        # Check if OTP is expired
        if "otp_expires" in user and user["otp_expires"] < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP code has expired"
            )
        
        # Mark user as verified and clear OTP
        user["is_verified"] = True
        user.pop("otp", None)
        user.pop("otp_expires", None)
        logger.info(f"Email verified successfully for user: {user['id']}")
        
        return {
            "status": "success",
            "message": "Email verified successfully!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed. Please try again."
        )

@auth_router.post("/resend-otp")
async def resend_otp(request: dict):
    """Resend OTP for email verification (mock implementation)"""
    try:
        email = request.get("email")
        logger.info(f"Resend OTP request for: {email}")
        
        # Find user by email
        user = None
        for u in users_db.values():
            if u["email"] == email:
                user = u
                break
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Generate and store OTP
        import secrets
        otp_code = str(secrets.randbelow(900000) + 100000)  # 6-digit OTP
        user["otp"] = otp_code
        user["otp_expires"] = datetime.now() + timedelta(minutes=10)
        
        # Try to send real email
        try:
            from email_service import get_email_service
            email_service = get_email_service()
            email_sent = await email_service.send_otp_email(
                email=email,
                otp_code=otp_code,
                user_name=user["username"]
            )
            
            if email_sent:
                logger.info(f"OTP sent successfully to: {email}")
                return {
                    "status": "success",
                    "message": "OTP sent successfully to your email."
                }
            else:
                logger.warning(f"Failed to send email to: {email}, but OTP generated: {otp_code}")
                return {
                    "status": "success",
                    "message": f"OTP generated: {otp_code} (email failed, check server logs)"
                }
        except Exception as e:
            logger.error(f"Email service error: {e}")
            logger.info(f"OTP generated: {otp_code}")
            return {
                "status": "success",
                "message": f"OTP generated: {otp_code} (email service unavailable)"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resend OTP error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend OTP. Please try again."
        )

@auth_router.post("/forget-password")
async def forget_password(request: dict):
    """Send password reset OTP (mock implementation)"""
    try:
        email = request.get("email")
        logger.info(f"Forget password request for: {email}")
        
        # Find user by email
        user = None
        for u in users_db.values():
            if u["email"] == email:
                user = u
                break
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Mock OTP sending (always succeed)
        logger.info(f"Password reset OTP sent successfully to: {email}")
        
        return {
            "status": "success",
            "message": "Password reset OTP sent successfully to your email."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Forget password error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send password reset OTP. Please try again."
        )

@auth_router.post("/reset-password")
async def reset_password(request: dict):
    """Reset password with OTP (mock implementation)"""
    try:
        email = request.get("email")
        otp_code = request.get("otp_code")
        new_password = request.get("new_password")
        
        logger.info(f"Password reset attempt for: {email}")
        
        # Find user by email
        user = None
        for u in users_db.values():
            if u["email"] == email:
                user = u
                break
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Mock OTP verification (always succeed)
        logger.info(f"Password reset successful for: {email}")
        
        # Update password in memory (mock)
        user["password"] = new_password
        
        return {
            "status": "success",
            "message": "Password reset successfully! You can now log in with your new password."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password. Please try again."
        )

@auth_router.get("/health")
async def auth_health():
    """Authentication service health check"""
    return {
        "status": "healthy",
        "service": "authentication",
        "users_count": len(users_db),
        "endpoints": [
            "signup", "login", "verify-email", "resend-otp", "forget-password", "reset-password"
        ]
    }

@auth_router.get("/debug/users")
async def debug_users():
    """Debug endpoint to see users in memory"""
    return {
        "users_count": len(users_db),
        "users": list(users_db.values())
    }
