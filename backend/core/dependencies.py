"""
FastAPI Dependencies

Reusable dependencies for dependency injection.
"""

from fastapi import Header, HTTPException, status, Depends
from typing import Optional
import jwt

from core.auth import verify_jwt_token
from core.database import get_user_by_id
from config import settings


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Dependency to get the current authenticated user.
    
    Args:
        authorization: Authorization header with Bearer token
        
    Returns:
        User dictionary with id, username, email
        
    Raises:
        HTTPException: If token is missing, invalid, or user not found
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    try:
        # Extract token from "Bearer <token>"
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme"
            )
        
        # Verify JWT token
        payload = verify_jwt_token(token)
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Get user from database
        user = get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"]
        }
        
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


# Alias for backward compatibility
verify_token = get_current_user
