"""
Authentication API Endpoints
Handles user registration, login, and authentication
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta
import logging
from database import db_manager
from models import User, OTP
from utils import hash_password, verify_password, create_access_token, verify_token
from email_service import get_email_service
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets

logger = logging.getLogger(__name__)

# Create router
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

# Security
security = HTTPBearer()

# Pydantic models
class UserSignup(BaseModel):
    username: str
    email: EmailStr
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
    created_at: datetime

class LoginResponse(BaseModel):
    status: str
    token: str
    user: UserResponse

class SignupResponse(BaseModel):
    status: str
    message: str
    user: Optional[UserResponse] = None

class VerifyEmailRequest(BaseModel):
    email: str
    otp_code: str

class ResendOtpRequest(BaseModel):
    email: str

class ForgetPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    email: str
    otp_code: str
    new_password: str

# Helper functions
def get_db():
    """Get database session"""
    return db_manager.get_db()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Get current authenticated user"""
    try:
        token = credentials.credentials
        payload = verify_token(token)
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Authentication endpoints
@auth_router.post("/signup", response_model=SignupResponse)
async def signup_user(user_data: UserSignup, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        logger.info(f"Signup attempt for username: {user_data.username}, email: {user_data.email}")
        
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()
        
        if existing_user:
            if existing_user.username == user_data.username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already exists"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already exists"
                )
        
        # Hash password (truncate to 72 bytes for bcrypt compatibility)
        password_to_hash = user_data.password[:72] if len(user_data.password) > 72 else user_data.password
        hashed_password = hash_password(password_to_hash)
        
        # Create new user
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            password=hashed_password,
            contact=user_data.contact,
            is_verified=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"User created successfully: {new_user.id}")
        
        return SignupResponse(
            status="success",
            message="Account created successfully! You can now log in.",
            user=UserResponse(
                id=new_user.id,
                username=new_user.username,
                email=new_user.email,
                contact=new_user.contact,
                is_verified=new_user.is_verified,
                created_at=new_user.created_at
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        import traceback
        logger.error(f"Signup traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Signup failed: {str(e)}"
        )

@auth_router.post("/login", response_model=LoginResponse)
async def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return token"""
    try:
        logger.info(f"Login attempt for username: {user_data.username}")
        
        # Find user by username or email
        user = db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.username)
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Verify password
        if not verify_password(user_data.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Create access token
        access_token_expires = timedelta(hours=24)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        logger.info(f"User logged in successfully: {user.id}")
        
        return LoginResponse(
            status="success",
            token=access_token,
            user=UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                contact=user.contact,
                is_verified=user.is_verified,
                created_at=user.created_at
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
async def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify user email with OTP (mock implementation)"""
    try:
        logger.info(f"Email verification attempt for: {request.email}")
        
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Find valid OTP for user
        otp_record = db.query(OTP).filter(
            OTP.user_id == user.id,
            OTP.otp_code == request.otp_code,
            OTP.expires_at > datetime.utcnow()
        ).first()
        
        if not otp_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP code"
            )
        
        # Update user verification status
        user.is_verified = True
        user.updated_at = datetime.utcnow()
        db.delete(otp_record)  # Remove used OTP
        db.commit()
        
        logger.info(f"Email verified successfully for user: {user.id}")
        
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
async def resend_otp(request: ResendOtpRequest, db: Session = Depends(get_db)):
    """Resend OTP for email verification (mock implementation)"""
    try:
        logger.info(f"Resend OTP request for: {request.email}")
        
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Generate OTP code
        otp_code = str(secrets.randbelow(900000) + 100000)  # 6-digit code
        expires_at = datetime.utcnow() + timedelta(minutes=10)  # 10 minutes expiry
        
        # Store OTP in database
        otp_record = OTP(
            user_id=user.id,
            otp_code=otp_code,
            expires_at=expires_at
        )
        db.add(otp_record)
        db.commit()
        
        # Send OTP email
        email_service = get_email_service()
        email_sent = await email_service.send_otp_email(
            email=request.email,
            otp_code=otp_code,
            user_name=user.username
        )
        
        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP email. Please try again."
            )
        
        logger.info(f"OTP sent successfully to: {request.email}")
        
        return {
            "status": "success",
            "message": "OTP sent successfully to your email."
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
async def forget_password(request: ForgetPasswordRequest, db: Session = Depends(get_db)):
    """Send password reset OTP (mock implementation)"""
    try:
        logger.info(f"Forget password request for: {request.email}")
        
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Generate OTP code
        otp_code = str(secrets.randbelow(900000) + 100000)  # 6-digit code
        expires_at = datetime.utcnow() + timedelta(minutes=10)  # 10 minutes expiry
        
        # Store OTP in database
        otp_record = OTP(
            user_id=user.id,
            otp_code=otp_code,
            expires_at=expires_at
        )
        db.add(otp_record)
        db.commit()
        
        # Send password reset email
        email_service = get_email_service()
        email_sent = await email_service.send_password_reset_email(
            email=request.email,
            otp_code=otp_code,
            user_name=user.username
        )
        
        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send password reset email. Please try again."
            )
        
        logger.info(f"Password reset OTP sent successfully to: {request.email}")
        
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
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password with OTP (mock implementation)"""
    try:
        logger.info(f"Password reset attempt for: {request.email}")
        
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Mock OTP verification (accept any 6-digit code)
        # Find valid OTP for user
        otp_record = db.query(OTP).filter(
            OTP.user_id == user.id,
            OTP.otp_code == request.otp_code,
            OTP.expires_at > datetime.utcnow()
        ).first()
        
        if otp_record:
            # Hash new password (truncate to 72 bytes for bcrypt compatibility)
            password_to_hash = request.new_password[:72] if len(request.new_password) > 72 else request.new_password
            hashed_password = hash_password(password_to_hash)
            user.password = hashed_password
            user.updated_at = datetime.utcnow()
            db.delete(otp_record)  # Remove used OTP
            db.commit()
            
            logger.info(f"Password reset successfully for user: {user.id}")
            
            return {
                "status": "success",
                "message": "Password reset successfully!"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP code"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed. Please try again."
        )

@auth_router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        contact=current_user.contact,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at
    )

@auth_router.get("/health")
async def auth_health():
    """Authentication service health check"""
    return {
        "status": "healthy",
        "service": "authentication",
        "endpoints": [
            "signup", "login", "verify-email", "resend-otp",
            "forget-password", "reset-password", "me"
        ]
    }

@auth_router.get("/debug/db")
async def debug_database():
    """Debug database connection"""
    try:
        db = get_db()
        # Try a simple query
        result = db.query(User).limit(1).all()
        return {
            "status": "success",
            "message": "Database connection working",
            "user_count": len(result)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Database connection failed: {str(e)}",
            "error_type": type(e).__name__
        }

@auth_router.get("/debug/env")
async def debug_environment():
    """Debug environment variables"""
    import os
    return {
        "MAIL_USERNAME": os.getenv("MAIL_USERNAME", "NOT_SET"),
        "MAIL_PASSWORD": "***" if os.getenv("MAIL_PASSWORD") else "NOT_SET",
        "MAIL_FROM": os.getenv("MAIL_FROM", "NOT_SET"),
        "MAIL_SERVER": os.getenv("MAIL_SERVER", "NOT_SET"),
        "MAIL_PORT": os.getenv("MAIL_PORT", "NOT_SET"),
        "DB_HOST": os.getenv("DB_HOST", "NOT_SET"),
        "DB_USER": os.getenv("DB_USER", "NOT_SET"),
        "DB_NAME": os.getenv("DB_NAME", "NOT_SET")
    }
