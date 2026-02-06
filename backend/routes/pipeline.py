"""
MOSDAC Pipeline route
- POST /pipeline/run - Run full data download -> analysis pipeline
"""

import os
import logging
import pandas as pd
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from core import get_current_user
from mosdac_manager import mosdac_manager
from routes.analysis import get_analysis_engine, ANALYSIS_DIR

router = APIRouter()
logger = logging.getLogger(__name__)


class PipelineRequest(BaseModel):
    username: str
    password: str
    dataset_id: str
    start_date: str
    end_date: str
    bounding_box: str = ""


@router.post("/pipeline/run")
async def run_pipeline(request: PipelineRequest, current_user: dict = Depends(get_current_user)):
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
            raise HTTPException(
                status_code=500, 
                detail=f"Download failed: {dl_res.get('error') or dl_res.get('message')}"
            )
        
        # 2. Analysis Phase
        logger.info("Starting Pipeline: Analysis Phase")
        download_dir = mosdac_manager.config.get('download_settings', {}).get('download_path') if hasattr(mosdac_manager, 'config') else os.path.join(mosdac_manager.working_dir, "downloads")
        
        # Verify downloads exist
        if not os.path.exists(download_dir):
            raise HTTPException(status_code=404, detail="No data downloaded to process.")
        
        engine = get_analysis_engine()
        results = engine.process_directory(download_dir)
        
        # 3. Persistence
        if results:
            df = pd.DataFrame(results)
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
