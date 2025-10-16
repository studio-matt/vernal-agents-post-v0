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
from models import User
from utils import hash_password, verify_password, create_access_token, verify_token
from email_service import get_email_service
from sqlalchemy.orm import Session
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
        
        # Hash password
        hashed_password = hash_password(user_data.password)
        
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
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Signup failed. Please try again."
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
        
        # Mock OTP verification (accept any 6-digit code)
        if len(request.otp_code) == 6 and request.otp_code.isdigit():
            user.is_verified = True
            user.updated_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Email verified successfully for user: {user.id}")
            
            return {
                "status": "success",
                "message": "Email verified successfully!"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP code"
            )
        
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
        if len(request.otp_code) == 6 and request.otp_code.isdigit():
            # Hash new password
            hashed_password = hash_password(request.new_password)
            user.password = hashed_password
            user.updated_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Password reset successfully for user: {user.id}")
            
            return {
                "status": "success",
                "message": "Password reset successfully!"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP code"
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
