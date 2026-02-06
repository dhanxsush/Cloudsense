from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi import Header
from pydantic import BaseModel, EmailStr
from contextlib import asynccontextmanager
import os
import numpy as np
import logging

# CRITICAL: Load environment variables BEFORE importing auth
from dotenv import load_dotenv
load_dotenv()

from db import (
    init_db, create_user, get_user_by_email, get_user_by_id,
    create_analysis, update_analysis_status, get_analysis, get_recent_analyses,
    save_analysis_results, get_analysis_results, save_analysis_metadata, get_analysis_metadata
)
from auth import hash_password, verify_password, create_jwt_token, verify_jwt_token
import jwt  # For exception types in verify_token
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup and shutdown"""
    init_db()
    logger.info("Database initialized")
    yield

app = FastAPI(title="CloudSense API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:8080",
        "http://localhost:8081",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "message": "CloudSense API is running"}

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

from fastapi.staticfiles import StaticFiles
import pandas as pd
from typing import List, Optional

# Use TCC Analysis Engine (uses new modular system)
from modules.pipeline import TCCPipeline
analysis_engine = TCCPipeline()
logger.info("TCC Pipeline (modular) loaded successfully")

# Mount the analysis directory to serve images (e.g., cyclone_trajectory_smoothed.png)
# We assume the analysis folder is at "../training" relative to backend
ANALYSIS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "training")
if not os.path.exists(ANALYSIS_DIR):
    os.makedirs(ANALYSIS_DIR)

app.mount("/static/analysis", StaticFiles(directory=ANALYSIS_DIR), name="analysis")

@app.get("/api/analysis/trajectory")
async def get_trajectory(current_user: dict = Depends(verify_token)):
    """Returns the smoothed Kalman trajectory data"""
    csv_path = os.path.join(ANALYSIS_DIR, "trajectory_kalman.csv")
    if not os.path.exists(csv_path):
        return {"error": "Trajectory data not found. Please run analysis first."}
    
    try:
        df = pd.read_csv(csv_path)
        # Convert NaN to None for JSON compliance
        df = df.replace({np.nan: None})
        return df.to_dict(orient="records")
    except (FileNotFoundError, pd.errors.EmptyDataError, ValueError) as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/clusters")
async def get_clusters(current_user: dict = Depends(verify_token)):
    """
    Returns the latest cluster stats.
    Priority: Live Data > Historical Data (Michaung)
    """
    live_path = os.path.join(ANALYSIS_DIR, "live_trajectory.csv")
    historical_path = os.path.join(ANALYSIS_DIR, "trajectory_kalman.csv")
    
    active_path = None
    data_source = "Unknown"
    
    if os.path.exists(live_path):
        active_path = live_path
        data_source = "MOSDAC (Live)"
    elif os.path.exists(historical_path):
        active_path = historical_path
        data_source = "Historical (Michaung)"
    
    if not active_path:
         return []
         
    try:
        df = pd.read_csv(active_path)
        if df.empty:
            return []
            
        # Return the last known state as the "Active" cluster
        last_row = df.iloc[-1]
        
        return [{
            "id": f"TCC-{last_row.get('timestamp', 'Unknown')}",
            "centroidLat": last_row.get('centroid_lat', last_row.get('smooth_cy', 0)), 
            "centroidLon": last_row.get('centroid_lon', last_row.get('smooth_cx', 0)), 
            "avgBT": last_row.get('mean_bt', last_row.get('avg_bt', 0)),  # Use actual BT from data
            "radius": last_row.get('radius_km', np.sqrt(last_row.get('area_km2', last_row.get('area_pixels_512', 0) * 16) / np.pi) if 'area_km2' in last_row or 'area_pixels_512' in last_row else 0),  # Calculate from actual area
            "status": "active",
            "lastUpdate": last_row.get('timestamp', 'Unknown'),
            "source": data_source
        }]
    except (FileNotFoundError, pd.errors.EmptyDataError, ValueError, KeyError) as e:
        logger.error(f"Error loading clusters: {e}")
        return []

from mosdac_manager import mosdac_manager
# Note: analysis_engine is already initialized above (lines 174-181)

class PipelineRequest(BaseModel):
    username: str
    password: str
    dataset_id: str
    start_date: str
    end_date: str
    bounding_box: str = ""

@app.post("/api/pipeline/run")
async def run_pipeline(request: PipelineRequest, current_user: dict = Depends(verify_token)):
    """
    Orchestrates the full Data -> Analysis -> UI pipeline.
    1. Downloads data via MOSDAC (mdapi).
    2. Runs Inference on the new files.
    3. Returns the live results.
    """
    try:
        # 1. Download Phase
        logger.info("Starting Pipeline: Download Phase")
        mosdac_manager.create_config(
            username=request.username,
            password=request.password,
            dataset_id=request.dataset_id,
            start_date=request.start_date,
            end_date=request.end_date,
            bounding_box=request.bounding_box
        )
        
        # Run mdapi
        dl_res = mosdac_manager.run_downloader()
        if dl_res['status'] != 'success':
             raise HTTPException(status_code=500, detail=f"Download failed: {dl_res.get('error') or dl_res.get('message')}")
        
        # 2. Analysis Phase
        logger.info("Starting Pipeline: Analysis Phase")
        download_dir = mosdac_manager.config.get('download_settings', {}).get('download_path') if hasattr(mosdac_manager, 'config') else os.path.join(mosdac_manager.working_dir, "downloads")
        
        # Verify downloads exist
        if not os.path.exists(download_dir):
            raise HTTPException(status_code=404, detail="No data downloaded to process.")
            
        results = analysis_engine.process_directory(download_dir)
        
        # 3. Persistence (Simple CSV append for now)
        # In production, save to DB
        if results:
            df = pd.DataFrame(results)
            # Save to a 'live' csv
            live_path = os.path.join(ANALYSIS_DIR, "live_trajectory.csv")
            df.to_csv(live_path, index=False)
             
        return {
            "status": "success", 
            "message": f"Pipeline Complete. Processed {len(results)} frames.", 
            "data": results,
            "source": "MOSDAC Real-Time"
        }
        
    except (FileNotFoundError, PermissionError, OSError, RuntimeError) as e:
        logger.error(f"Pipeline Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


from fastapi import UploadFile, File
import shutil

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), current_user: dict = Depends(verify_token)):
    """
    Upload file and create analysis.
    Returns analysis_id for tracking.
    """
    try:
        # 1. Validate file type (security: only allow HDF5 files)
        ALLOWED_EXTENSIONS = {'.h5', '.hdf5', '.HDF5', '.H5'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in {ext.lower() for ext in ALLOWED_EXTENSIONS}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Only HDF5 files (.h5, .hdf5) are allowed. Got: {file_ext}"
            )
        
        # 2. Validate file size (security: prevent disk exhaustion)
        MAX_FILE_SIZE_MB = 500
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE_MB}MB. Got: {file_size / (1024*1024):.2f}MB"
            )
        
        # 3. Generate unique analysis ID
        analysis_id = str(uuid.uuid4())
        
        # 4. Sanitize filename and use UUID-based storage (security: prevent path traversal)
        # Extract safe filename (remove path components)
        safe_filename = os.path.basename(file.filename)
        # Remove any potentially dangerous characters
        safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in '._-')
        
        # Use UUID for actual storage to prevent collisions
        storage_filename = f"{analysis_id}{file_ext}"
        
        # 5. Save uploaded file
        upload_dir = os.path.join(ANALYSIS_DIR, "manual_uploads")
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            
        file_path = os.path.join(upload_dir, storage_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logger.info(f"File uploaded: {file.filename} -> {analysis_id}")
        
        # 3. Create analysis record in database
        create_analysis(
            analysis_id=analysis_id,
            filename=file.filename,
            file_path=file_path,
            source="manual_upload"
        )
        
        # 7. Run analysis directly on this machine
        logger.info(f"Processing {safe_filename} with TCC engine...")
        results = analysis_engine.process_frame(file_path)  # TCCPipeline extracts timestamp from file
        
        # 5. Save results to database
        if results:
            save_analysis_results(analysis_id, results)
            
            # Compute metadata
            all_areas = [r.get('area_km2', 0) for r in results if 'area_km2' in r]
            all_bts = [r.get('mean_bt', 0) for r in results if 'mean_bt' in r]
            
            metadata = {
                'total_frames': len(results),
                'min_bt': min(all_bts) if all_bts else None,
                'max_bt': max(all_bts) if all_bts else None,
                'mean_bt': sum(all_bts) / len(all_bts) if all_bts else None,
                'total_area': sum(all_areas) if all_areas else None
            }
            save_analysis_metadata(analysis_id, metadata)
            
            update_analysis_status(analysis_id, 'complete')
            logger.info(f"✓ Analysis complete: {len(results)} clusters detected")
        else:
            update_analysis_status(analysis_id, 'failed')
            logger.warning(f"✗ No clusters detected")
            
        return {
            "analysis_id": analysis_id,
            "status": "complete" if results else "failed",
            "message": f"Processed {file.filename}",
            "total_frames": len(results) if results else 0
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (from validation)
        raise
    except (OSError, IOError, RuntimeError) as e:
        logger.error(f"Upload Error: {e}")
        if 'analysis_id' in locals():
            update_analysis_status(analysis_id, 'failed')
        raise HTTPException(status_code=500, detail=str(e))

# Analysis API Endpoints
@app.get("/api/analysis/{analysis_id}/status")
async def get_analysis_status_endpoint(analysis_id: str, current_user: dict = Depends(verify_token)):
    """Get status of an analysis."""
    analysis = get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return {
        "analysis_id": analysis['id'],
        "status": analysis['status'],
        "filename": analysis['filename'],
        "upload_timestamp": analysis['upload_timestamp'],
        "source": analysis['source']
    }

@app.get("/api/analysis/{analysis_id}/trajectory")
async def get_analysis_trajectory_endpoint(analysis_id: str, current_user: dict = Depends(verify_token)):
    """Get trajectory data for an analysis."""
    analysis = get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    results = get_analysis_results(analysis_id)
    
    if not results:
        return []
    
    return results

@app.get("/api/analysis/{analysis_id}/metadata")
async def get_analysis_metadata_endpoint(analysis_id: str, current_user: dict = Depends(verify_token)):
    """Get metadata for an analysis."""
    metadata = get_analysis_metadata(analysis_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Metadata not found")
    
    return metadata

@app.get("/api/analyses/recent")
async def list_recent_analyses_endpoint(limit: int = 10, current_user: dict = Depends(verify_token)):
    """Get list of recent analyses."""
    analyses = get_recent_analyses(limit)
    return analyses

# ================= PREDICTION & REPORT ENDPOINTS =================

@app.get("/api/analysis/{analysis_id}/predictions")
async def get_predictions_endpoint(analysis_id: str, steps: int = 6, current_user: dict = Depends(verify_token)):
    """
    Get future position predictions for tracked TCCs.
    
    Uses Kalman filter velocity estimates to predict movement.
    Default: 6 steps = 3 hours at 30-minute intervals.
    """
    analysis = get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Get predictions from pipeline if available
    predictions = analysis_engine.get_predictions(steps=steps)
    
    return {
        "analysis_id": analysis_id,
        "predictions": predictions,
        "status": "success"
    }

@app.post("/api/analysis/{analysis_id}/report")
async def generate_report_endpoint(analysis_id: str, current_user: dict = Depends(verify_token)):
    """
    Generate comprehensive analysis report.
    
    Creates NetCDF, CSV, JSON, and predictions files.
    """
    analysis = get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Generate report
    report_dir = os.path.join(ANALYSIS_DIR, "reports", analysis_id)
    try:
        report = analysis_engine.generate_report(report_dir)
        return {
            "analysis_id": analysis_id,
            "status": "complete",
            "report": report,
            "download_urls": {
                "netcdf": f"/api/analysis/{analysis_id}/download/netcdf",
                "csv": f"/api/analysis/{analysis_id}/download/csv",
                "json": f"/api/analysis/{analysis_id}/download/json",
                "predictions": f"/api/analysis/{analysis_id}/download/predictions"
            }
        }
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/{analysis_id}/download/{file_type}")
async def download_report_file(analysis_id: str, file_type: str, current_user: dict = Depends(verify_token)):
    """
    Download analysis report files.
    
    file_type: netcdf | csv | json | predictions
    """
    file_map = {
        "netcdf": "tcc_trajectory.nc",
        "csv": "tcc_trajectory.csv",
        "json": "tcc_analysis.json",
        "predictions": "tcc_predictions.json"
    }
    
    if file_type not in file_map:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Options: {list(file_map.keys())}")
    
    file_path = os.path.join(ANALYSIS_DIR, "reports", analysis_id, file_map[file_type])
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report file not found. Generate report first.")
    
    media_types = {
        "netcdf": "application/x-netcdf",
        "csv": "text/csv",
        "json": "application/json",
        "predictions": "application/json"
    }
    
    return FileResponse(
        file_path,
        media_type=media_types.get(file_type, "application/octet-stream"),
        filename=file_map[file_type]
    )

# ================= CHATBOT ENDPOINTS =================

from modules.chatbot import chatbot

class ChatRequest(BaseModel):
    message: str
    include_analysis_context: bool = False
    analysis_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_length: int

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, current_user: dict = Depends(verify_token)):
    """
    Chat with CloudSense AI assistant.
    
    The assistant specializes in:
    - Tropical Cloud Cluster analysis
    - Satellite data interpretation
    - Weather patterns and cyclone formation
    """
    context = None
    
    # Include analysis context if requested
    if request.include_analysis_context and request.analysis_id:
        results = get_analysis_results(request.analysis_id)
        if results:
            context = f"Analysis {request.analysis_id}: {len(results)} detections"
    
    response = chatbot.chat(request.message, include_context=context)
    
    return ChatResponse(
        response=response,
        conversation_length=len(chatbot.conversation_history)
    )

@app.post("/api/chat/clear")
async def clear_chat_history(current_user: dict = Depends(verify_token)):
    """Clear chatbot conversation history."""
    chatbot.clear_history()
    return {"status": "cleared", "message": "Conversation history cleared"}

@app.post("/api/chat/summarize/{analysis_id}")
async def summarize_analysis(analysis_id: str, current_user: dict = Depends(verify_token)):
    """
    Get AI-generated summary of analysis results.
    """
    analysis = get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    results = get_analysis_results(analysis_id)
    if not results:
        raise HTTPException(status_code=404, detail="No analysis results")
    
    summary = chatbot.get_analysis_summary({
        "analysis_id": analysis_id,
        "total_detections": len(results),
        "clusters": results[:5]  # First 5 for context
    })
    
    return {
        "analysis_id": analysis_id,
        "summary": summary,
        "total_detections": len(results)
    }

if __name__ == "__main__":

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
