"""
Analysis routes
- GET /analysis/trajectory - Get Kalman trajectory data
- GET /analysis/clusters - Get latest cluster stats
- GET /analysis/{id}/status - Get analysis status
- GET /analysis/{id}/trajectory - Get analysis trajectory
- GET /analysis/{id}/metadata - Get analysis metadata
- GET /analysis/{id}/predictions - Get predictions
- POST /analysis/{id}/report - Generate report
- GET /analysis/{id}/download/{type} - Download report files
- GET /analyses/recent - List recent analyses
"""

import os
import logging
import numpy as np
import pandas as pd
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse

from core import (
    get_current_user,
    get_analysis,
    get_analysis_results,
    get_analysis_metadata,
    get_recent_analyses
)
from modules.pipeline import TCCPipeline

router = APIRouter()
logger = logging.getLogger(__name__)

# Directory for analysis outputs
ANALYSIS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
    "training"
)

# Shared analysis engine instance
_analysis_engine: Optional[TCCPipeline] = None


def get_analysis_engine() -> TCCPipeline:
    """Get or create the shared analysis engine instance."""
    global _analysis_engine
    if _analysis_engine is None:
        _analysis_engine = TCCPipeline()
        logger.info("TCC Pipeline initialized")
    return _analysis_engine


# ==================== Trajectory & Clusters ====================

@router.get("/analysis/trajectory")
async def get_trajectory(current_user: dict = Depends(get_current_user)):
    """Returns the smoothed Kalman trajectory data"""
    csv_path = os.path.join(ANALYSIS_DIR, "trajectory_kalman.csv")
    if not os.path.exists(csv_path):
        return {"error": "Trajectory data not found. Please run analysis first."}
    
    try:
        df = pd.read_csv(csv_path)
        df = df.replace({np.nan: None})
        return df.to_dict(orient="records")
    except (FileNotFoundError, pd.errors.EmptyDataError, ValueError) as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/clusters")
async def get_clusters(current_user: dict = Depends(get_current_user)):
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
            
        last_row = df.iloc[-1]
        
        return [{
            "id": f"TCC-{last_row.get('timestamp', 'Unknown')}",
            "centroidLat": last_row.get('centroid_lat', last_row.get('smooth_cy', 0)), 
            "centroidLon": last_row.get('centroid_lon', last_row.get('smooth_cx', 0)), 
            "avgBT": last_row.get('mean_bt', last_row.get('avg_bt', 0)),
            "radius": last_row.get('radius_km', np.sqrt(last_row.get('area_km2', last_row.get('area_pixels_512', 0) * 16) / np.pi) if 'area_km2' in last_row or 'area_pixels_512' in last_row else 0),
            "status": "active",
            "lastUpdate": last_row.get('timestamp', 'Unknown'),
            "source": data_source
        }]
    except (FileNotFoundError, pd.errors.EmptyDataError, ValueError, KeyError) as e:
        logger.error(f"Error loading clusters: {e}")
        return []


# ==================== Analysis CRUD ====================

@router.get("/analysis/{analysis_id}/status")
async def get_analysis_status_endpoint(analysis_id: str, current_user: dict = Depends(get_current_user)):
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


@router.get("/analysis/{analysis_id}/trajectory")
async def get_analysis_trajectory_endpoint(analysis_id: str, current_user: dict = Depends(get_current_user)):
    """Get trajectory data for an analysis."""
    analysis = get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    results = get_analysis_results(analysis_id)
    
    if not results:
        return []
    
    return results


@router.get("/analysis/{analysis_id}/metadata")
async def get_analysis_metadata_endpoint(analysis_id: str, current_user: dict = Depends(get_current_user)):
    """Get metadata for an analysis."""
    metadata = get_analysis_metadata(analysis_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Metadata not found")
    
    return metadata


@router.get("/analyses/recent")
async def list_recent_analyses_endpoint(limit: int = 10, current_user: dict = Depends(get_current_user)):
    """Get list of recent analyses."""
    analyses = get_recent_analyses(limit)
    return analyses


# ==================== Predictions & Reports ====================

@router.get("/analysis/{analysis_id}/predictions")
async def get_predictions_endpoint(analysis_id: str, steps: int = 6, current_user: dict = Depends(get_current_user)):
    """
    Get future position predictions for tracked TCCs.
    Uses Kalman filter velocity estimates to predict movement.
    Default: 6 steps = 3 hours at 30-minute intervals.
    """
    analysis = get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    engine = get_analysis_engine()
    predictions = engine.get_predictions(steps=steps)
    
    return {
        "analysis_id": analysis_id,
        "predictions": predictions,
        "status": "success"
    }


@router.post("/analysis/{analysis_id}/report")
async def generate_report_endpoint(analysis_id: str, current_user: dict = Depends(get_current_user)):
    """
    Generate comprehensive analysis report.
    Creates NetCDF, CSV, JSON, and predictions files.
    """
    analysis = get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    report_dir = os.path.join(ANALYSIS_DIR, "reports", analysis_id)
    try:
        engine = get_analysis_engine()
        report = engine.generate_report(report_dir)
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


@router.get("/analysis/{analysis_id}/download/{file_type}")
async def download_report_file(analysis_id: str, file_type: str, current_user: dict = Depends(get_current_user)):
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
