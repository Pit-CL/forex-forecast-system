"""
Authentication Router
"""
from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Union
from typing import Optional
import logging
import os
from datetime import datetime

# Import auth service (will be created in parent directory)
import sys
sys.path.append('..')
from auth.auth_service import AuthService, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# Request/Response models
class LoginRequest(BaseModel):
    email: str  # Changed from EmailStr to str for simplicity
    password: Optional[str] = None  # Optional for magic link


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    expires_in: int = 43200  # 12 hours in seconds


class MagicLinkRequest(BaseModel):
    email: str


class UserInfo(BaseModel):
    email: str
    is_authorized: bool
    authenticated_at: datetime


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Login with email (must be in whitelist)
    For demo purposes, any password works if email is authorized
    """
    # Check if email is authorized
    if not AuthService.check_email_authorized(request.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Email {request.email} is not authorized to access this system"
        )

    # For production, implement proper password verification
    # For now, accept any password for authorized emails
    if request.password and len(request.password) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot be empty"
        )

    # Generate token
    access_token = AuthService.create_access_token(request.email)

    logger.info(f"User {request.email} logged in successfully")

    return LoginResponse(
        access_token=access_token,
        email=request.email
    )


@router.post("/magic-link")
async def request_magic_link(request: MagicLinkRequest, background_tasks: BackgroundTasks):
    """
    Request a magic link for passwordless authentication
    """
    # Check if email is authorized
    if not AuthService.check_email_authorized(request.email):
        # Don't reveal if email is not in whitelist (security)
        return {"message": "If your email is authorized, you will receive a magic link"}

    # Generate magic link
    magic_link = AuthService.generate_magic_link(request.email)

    # In production, send email here
    # For development, log the link
    logger.info(f"Magic link for {request.email}: {magic_link}")

    # Simulate email sending
    # background_tasks.add_task(send_email, request.email, magic_link)

    return {
        "message": "If your email is authorized, you will receive a magic link",
        "dev_link": magic_link if os.environ.get("DEV_MODE") == "true" else None
    }


@router.get("/verify")
async def verify_magic_link(token: str):
    """
    Verify magic link token
    """
    try:
        # Verify token directly
        import jwt
        from auth.auth_service import SECRET_KEY, ALGORITHM

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        if not email or not AuthService.check_email_authorized(email):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired link"
            )

        # Generate new access token
        access_token = AuthService.create_access_token(email)

        return LoginResponse(
            access_token=access_token,
            email=email
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired link"
        )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user: str = Depends(get_current_user)):
    """
    Get current user information
    """
    return UserInfo(
        email=current_user,
        is_authorized=True,
        authenticated_at=datetime.now()
    )


@router.get("/whitelist")
async def get_whitelist(current_user: str = Depends(get_current_user)):
    """
    Get list of authorized emails (only for authenticated users)
    """
    # Only allow certain admin emails to see the full whitelist
    admin_emails = {"rafael@cavara.cl"}

    if current_user not in admin_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view the whitelist"
        )

    return {
        "authorized_emails": AuthService.get_authorized_emails(),
        "total": len(AuthService.get_authorized_emails())
    }


@router.post("/logout")
async def logout(current_user: str = Depends(get_current_user)):
    """
    Logout (client should delete token)
    """
    logger.info(f"User {current_user} logged out")
    return {"message": "Logged out successfully"}


@router.get("/check")
async def check_auth_status():
    """
    Check if authentication is enabled
    """
    return {
        "auth_required": True,
        "whitelist_enabled": True,
        "total_authorized_users": len(AuthService.get_authorized_emails())
    }