"""
User-related Pydantic models
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class SignupRequest(BaseModel):
    """Request model for user signup."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Response model for successful login."""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Response model for user data."""
    id: int
    username: str
    email: str
    created_at: Optional[datetime] = None


class TokenPayload(BaseModel):
    """JWT token payload."""
    user_id: int
    exp: Optional[int] = None
