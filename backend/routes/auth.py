"""
Authentication routes
- POST /signup - Register new user
- POST /login - Login with email/password  
- GET /verify - Verify JWT token
"""

from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
import jwt

from core import (
    hash_password, 
    verify_password, 
    create_jwt_token, 
    verify_jwt_token,
    create_user, 
    get_user_by_email, 
    get_user_by_id
)

router = APIRouter()


# ==================== Request/Response Models ====================

class SignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: dict


# ==================== Endpoints ====================

@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
    """Register a new user"""
    if len(request.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )
    
    user = get_user_by_email(request.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    password_hash = hash_password(request.password)
    user_id = create_user(request.username, request.email, password_hash)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    new_user = get_user_by_id(user_id)
    token_response = create_jwt_token(user_id, request.email)
    
    return AuthResponse(
        access_token=token_response["access_token"],
        token_type=token_response["token_type"],
        expires_in=token_response["expires_in"],
        user={
            "id": new_user["id"],
            "username": new_user["username"],
            "email": new_user["email"]
        }
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login user with email and password"""
    user = get_user_by_email(request.email)
    
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    token_response = create_jwt_token(user["id"], user["email"])
    
    return AuthResponse(
        access_token=token_response["access_token"],
        token_type=token_response["token_type"],
        expires_in=token_response["expires_in"],
        user={
            "id": user["id"],
            "username": user["username"],
            "email": user["email"]
        }
    )


@router.get("/verify")
async def verify_token(request: Request):
    """Verify JWT token and return user info"""
    authorization = request.headers.get("authorization")
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")

    try:
        payload = verify_jwt_token(token)
        user = get_user_by_id(int(payload["sub"]))
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
