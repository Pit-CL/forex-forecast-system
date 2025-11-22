"""
Authentication Service with Email Whitelist
"""
import os
import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# Configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 720  # 12 hours

# Whitelist of authorized emails
AUTHORIZED_EMAILS = {
    "valentina@cavara.cl",
    "catalina@cavara.cl",
    "rafael@cavara.cl"
}


class AuthService:
    """Handle authentication and authorization"""

    @staticmethod
    def create_access_token(email: str) -> str:
        """Create JWT access token"""
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode = {
            "sub": email,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
        """Verify JWT token and return email"""
        token = credentials.credentials
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Check if email is in whitelist
            if email not in AUTHORIZED_EMAILS:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Email not authorized to access this resource",
                )

            return email
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    def check_email_authorized(email: str) -> bool:
        """Check if email is in whitelist"""
        return email.lower() in {e.lower() for e in AUTHORIZED_EMAILS}

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return AuthService.hash_password(plain_password) == hashed_password

    @staticmethod
    def generate_magic_link(email: str) -> str:
        """Generate magic link for passwordless authentication"""
        token = AuthService.create_access_token(email)
        # In production, this would be a full URL
        return f"/auth/verify?token={token}"

    @staticmethod
    def get_authorized_emails() -> List[str]:
        """Get list of authorized emails"""
        return list(AUTHORIZED_EMAILS)


# Dependency for protected routes
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current authenticated user email"""
    return AuthService.verify_token(credentials)


# Optional: Allow certain routes without auth in development
def optional_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[str]:
    """Optional authentication - returns email or None"""
    if not credentials:
        return None
    try:
        return AuthService.verify_token(credentials)
    except HTTPException:
        return None