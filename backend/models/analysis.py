"""
Analysis-related Pydantic models
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class AnalysisCreate(BaseModel):
    """Model for creating a new analysis."""
    filename: str
    file_path: str
    source: str = "manual_upload"


class ClusterResult(BaseModel):
    """Model for a single cluster detection result."""
    track_id: Optional[int] = None
    cluster_id: int
    timestamp: str
    centroid_lat: float
    centroid_lon: float
    centroid_x: float
    centroid_y: float
    area_km2: float
    radius_km: float
    min_bt: float
    max_bt: float
    mean_bt: float
    aspect_ratio: float
    is_predicted: bool = False


class AnalysisMetadata(BaseModel):
    """Model for analysis metadata."""
    total_frames: Optional[int] = None
    min_bt: Optional[float] = None
    max_bt: Optional[float] = None
    mean_bt: Optional[float] = None
    total_area: Optional[float] = None


class AnalysisResponse(BaseModel):
    """Response model for analysis status."""
    analysis_id: str
    filename: str
    upload_timestamp: datetime
    status: str
    source: str


class AnalysisResultsResponse(BaseModel):
    """Response model for analysis results."""
    analysis_id: str
    status: str
    clusters: List[ClusterResult] = []
    total_detections: int = 0
    metadata: Optional[AnalysisMetadata] = None


class UploadResponse(BaseModel):
    """Response model for file upload."""
    analysis_id: str
    filename: str
    status: str
    message: str
