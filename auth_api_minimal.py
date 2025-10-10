"""
Minimal Authentication API Endpoints (No Database)
Handles user registration, login, and authentication without database dependency
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta
import logging
import jwt
import hashlib
import secrets

logger = logging.getLogger(__name__)

# Create router
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

# Security
security = HTTPBearer()

# In-memory storage for demo purposes
users_db = {}
tokens_db = {}

# JWT Secret (in production, use environment variable)
JWT_SECRET = "your-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"

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
def hash_password(password: str) -> str:
    """Hash password using SHA-256 (for demo purposes)"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    return hash_password(plain_password) == hashed_password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
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
        
        user = users_db.get(int(user_id))
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
async def signup_user(user_data: UserSignup):
    """Register a new user"""
    try:
        logger.info(f"Signup attempt for username: {user_data.username}, email: {user_data.email}")
        
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
        
        # Hash password
        hashed_password = hash_password(user_data.password)
        
        # Create new user
        user_id = len(users_db) + 1
        new_user = {
            "id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "password": hashed_password,
            "contact": user_data.contact,
            "is_verified": False,
            "created_at": datetime.utcnow()
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
                is_verified=new_user["is_verified"],
                created_at=new_user["created_at"]
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
        
        # Verify password
        if not verify_password(user_data.password, user["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Create access token
        access_token_expires = timedelta(hours=24)
        access_token = create_access_token(
            data={"sub": str(user["id"])}, expires_delta=access_token_expires
        )
        
        logger.info(f"User logged in successfully: {user['id']}")
        
        return LoginResponse(
            status="success",
            token=access_token,
            user=UserResponse(
                id=user["id"],
                username=user["username"],
                email=user["email"],
                contact=user["contact"],
                is_verified=user["is_verified"],
                created_at=user["created_at"]
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
async def verify_email(request: VerifyEmailRequest):
    """Verify user email with OTP (mock implementation)"""
    try:
        logger.info(f"Email verification attempt for: {request.email}")
        
        # Find user by email
        user = None
        for u in users_db.values():
            if u["email"] == request.email:
                user = u
                break
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Mock OTP verification (accept any 6-digit code)
        if len(request.otp_code) == 6 and request.otp_code.isdigit():
            user["is_verified"] = True
            logger.info(f"Email verified successfully for user: {user['id']}")
            
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
async def resend_otp(request: ResendOtpRequest):
    """Resend OTP for email verification (mock implementation)"""
    try:
        logger.info(f"Resend OTP request for: {request.email}")
        
        # Find user by email
        user = None
        for u in users_db.values():
            if u["email"] == request.email:
                user = u
                break
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Mock OTP sending (always succeed)
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
async def forget_password(request: ForgetPasswordRequest):
    """Send password reset OTP (mock implementation)"""
    try:
        logger.info(f"Forget password request for: {request.email}")
        
        # Find user by email
        user = None
        for u in users_db.values():
            if u["email"] == request.email:
                user = u
                break
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Mock password reset OTP sending
        logger.info(f"Password reset OTP sent successfully to: {request.email}")
        
        return {
            "status": "success",
            "message": "OTP sent for password reset."
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
async def reset_password(request: ResetPasswordRequest):
    """Reset password with OTP (mock implementation)"""
    try:
        logger.info(f"Password reset attempt for: {request.email}")
        
        # Find user by email
        user = None
        for u in users_db.values():
            if u["email"] == request.email:
                user = u
                break
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Mock OTP verification (accept any 6-digit code)
        if len(request.otp_code) == 6 and request.otp_code.isdigit():
            # Hash new password
            hashed_password = hash_password(request.new_password)
            user["password"] = hashed_password
            logger.info(f"Password reset successfully for user: {user['id']}")
            
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
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        contact=current_user["contact"],
        is_verified=current_user["is_verified"],
        created_at=current_user["created_at"]
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
