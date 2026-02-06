"""
CloudSense API - Minimal Pipeline
Upload H5 → Run Inference → Download 3 Outputs (mask.npy, mask.png, output.nc)
"""

from fastapi import FastAPI, HTTPException, Depends, status, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from contextlib import asynccontextmanager
from typing import Optional
import os
import shutil
import uuid
import logging

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from db import (
    init_db, create_user, get_user_by_email, get_user_by_id,
    create_analysis, update_analysis_status, get_analysis, get_recent_analyses,
    save_analysis_results, get_analysis_results
)
from auth import hash_password, verify_password, create_jwt_token, verify_jwt_token
import jwt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===================== APP SETUP =====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup"""
    init_db()
    logger.info("Database initialized")
    yield

app = FastAPI(title="CloudSense API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===================== DIRECTORIES =====================

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount output directory for static file serving
app.mount("/static/output", StaticFiles(directory=OUTPUT_DIR), name="output")


# ===================== AUTH MODELS =====================

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


# ===================== AUTH DEPENDENCY =====================

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


# ===================== HEALTH =====================

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "message": "CloudSense API is running"}


# ===================== AUTH ENDPOINTS =====================

@app.post("/api/auth/signup", response_model=AuthResponse)
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

@app.post("/api/auth/login", response_model=AuthResponse)
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

@app.get("/api/auth/verify")
async def verify_token_endpoint(request: Request):
    """Verify JWT token and return user info"""
    return await verify_token(request)


# ===================== UPLOAD & INFERENCE =====================

# Lazy load inference pipeline
_inference_pipeline = None

def get_inference_pipeline():
    """Lazy load the inference pipeline to avoid startup delays"""
    global _inference_pipeline
    if _inference_pipeline is None:
        from inference_engine import InferencePipeline
        _inference_pipeline = InferencePipeline()
        logger.info("Inference pipeline loaded")
    return _inference_pipeline


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), current_user: dict = Depends(verify_token)):
    """
    Upload H5 file and run inference.
    Returns analysis_id with paths to 3 outputs: mask.npy, mask.png, output.nc
    """
    try:
        # 1. Validate file type
        ALLOWED_EXTENSIONS = {'.h5', '.hdf5'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only HDF5 files (.h5, .hdf5) are allowed. Got: {file_ext}"
            )
        
        # 2. Validate file size (max 500MB)
        MAX_FILE_SIZE_MB = 500
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Max: {MAX_FILE_SIZE_MB}MB"
            )
        
        # 3. Generate unique analysis ID
        analysis_id = str(uuid.uuid4())
        
        # 4. Save uploaded file
        storage_filename = f"{analysis_id}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, storage_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"File uploaded: {file.filename} -> {analysis_id}")
        
        # 5. Create analysis record
        create_analysis(
            analysis_id=analysis_id,
            filename=file.filename,
            file_path=file_path,
            source="manual_upload"
        )
        
        # 6. Run inference
        logger.info(f"Running inference on {file.filename}...")
        pipeline = get_inference_pipeline()
        result = pipeline.process_file(file_path, OUTPUT_DIR, analysis_id)
        
        if result["success"]:
            update_analysis_status(analysis_id, "complete")
            save_analysis_results(analysis_id, result)
            
            return {
                "analysis_id": analysis_id,
                "status": "complete",
                "message": f"Processed {file.filename}",
                "outputs": {
                    "mask_npy": f"/api/download/{analysis_id}/mask.npy",
                    "mask_png": f"/api/download/{analysis_id}/mask.png",
                    "netcdf": f"/api/download/{analysis_id}/output.nc"
                },
                "tcc_pixels": result.get("tcc_pixels", 0)
            }
        else:
            update_analysis_status(analysis_id, "failed")
            raise HTTPException(status_code=500, detail=result.get("error", "Inference failed"))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== DOWNLOAD OUTPUTS =====================

@app.get("/api/download/{analysis_id}/{filename}")
async def download_output(analysis_id: str, filename: str, current_user: dict = Depends(verify_token)):
    """
    Download output files: mask.npy, mask.png, output.nc
    """
    # Validate filename
    ALLOWED_FILES = {"mask.npy", "mask.png", "output.nc"}
    if filename not in ALLOWED_FILES:
        raise HTTPException(status_code=400, detail=f"Invalid file. Options: {ALLOWED_FILES}")
    
    # Build file path
    file_path = os.path.join(OUTPUT_DIR, analysis_id, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Set media type
    media_types = {
        "mask.npy": "application/octet-stream",
        "mask.png": "image/png",
        "output.nc": "application/x-netcdf"
    }
    
    return FileResponse(
        file_path,
        media_type=media_types.get(filename, "application/octet-stream"),
        filename=f"{analysis_id}_{filename}"
    )


# ===================== EXPORTS LIST =====================

@app.get("/api/exports")
async def list_exports(current_user: dict = Depends(verify_token)):
    """List all available exports"""
    exports = []
    
    if os.path.exists(OUTPUT_DIR):
        for analysis_id in os.listdir(OUTPUT_DIR):
            analysis_dir = os.path.join(OUTPUT_DIR, analysis_id)
            if os.path.isdir(analysis_dir):
                files = os.listdir(analysis_dir)
                exports.append({
                    "analysis_id": analysis_id,
                    "files": files,
                    "download_urls": {
                        "mask_npy": f"/api/download/{analysis_id}/mask.npy" if "mask.npy" in files else None,
                        "mask_png": f"/api/download/{analysis_id}/mask.png" if "mask.png" in files else None,
                        "netcdf": f"/api/download/{analysis_id}/output.nc" if "output.nc" in files else None
                    }
                })
    
    return exports


# ===================== RECENT ANALYSES =====================

@app.get("/api/analyses/recent")
async def list_recent_analyses(limit: int = 10, current_user: dict = Depends(verify_token)):
    """Get list of recent analyses"""
    analyses = get_recent_analyses(limit)
    return analyses


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
