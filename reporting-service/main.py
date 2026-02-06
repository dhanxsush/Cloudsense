"""
CloudSense Reporting Service
Microservice for NetCDF export and CF-1.8 compliance
Port: 8002
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import logging
import os

from netcdf_generator import NetCDFGenerator

# Setup
app = FastAPI(title="CloudSense Reporting Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize generator
netcdf_generator = NetCDFGenerator()


# Request/Response Models
class GenerateNetCDFRequest(BaseModel):
    analysis_id: str
    database_path: str
    output_dir: str


class GenerateNetCDFResponse(BaseModel):
    analysis_id: str
    status: str
    file_path: str
    file_size: int
    message: str


# Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "reporting"
    }


@app.post("/generate-netcdf", response_model=GenerateNetCDFResponse)
async def generate_netcdf(request: GenerateNetCDFRequest):
    """
    Generate CF-1.8 compliant NetCDF file from analysis results.
    """
    try:
        logger.info(f"Generating NetCDF for analysis {request.analysis_id}")
        
        # Generate output filename
        output_filename = f"{request.analysis_id}.nc"
        output_path = os.path.join(request.output_dir, output_filename)
        
        # Ensure output directory exists
        os.makedirs(request.output_dir, exist_ok=True)
        
        # Generate NetCDF file
        file_path = netcdf_generator.generate(
            analysis_id=request.analysis_id,
            database_path=request.database_path,
            output_path=output_path
        )
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        logger.info(f"NetCDF generated: {file_path} ({file_size} bytes)")
        
        return GenerateNetCDFResponse(
            analysis_id=request.analysis_id,
            status="complete",
            file_path=file_path,
            file_size=file_size,
            message=f"NetCDF file generated successfully"
        )
        
    except Exception as e:
        logger.error(f"NetCDF generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
