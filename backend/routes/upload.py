"""
File upload route
- POST /upload - Upload HDF5 file and run analysis
"""

import os
import shutil
import uuid
import logging
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File

from core import (
    get_current_user,
    create_analysis,
    update_analysis_status,
    save_analysis_results,
    save_analysis_metadata
)
from routes.analysis import get_analysis_engine, ANALYSIS_DIR

router = APIRouter()
logger = logging.getLogger(__name__)

# File validation constants
ALLOWED_EXTENSIONS = {'.h5', '.hdf5', '.HDF5', '.H5'}
MAX_FILE_SIZE_MB = 500


@router.post("/upload")
async def upload_file(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """
    Upload file and create analysis.
    Returns analysis_id for tracking.
    """
    try:
        # 1. Validate file type
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in {ext.lower() for ext in ALLOWED_EXTENSIONS}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Only HDF5 files (.h5, .hdf5) are allowed. Got: {file_ext}"
            )
        
        # 2. Validate file size
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE_MB}MB. Got: {file_size / (1024*1024):.2f}MB"
            )
        
        # 3. Generate unique analysis ID
        analysis_id = str(uuid.uuid4())
        
        # 4. Sanitize filename
        safe_filename = os.path.basename(file.filename)
        safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in '._-')
        storage_filename = f"{analysis_id}{file_ext}"
        
        # 5. Save uploaded file
        upload_dir = os.path.join(ANALYSIS_DIR, "manual_uploads")
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            
        file_path = os.path.join(upload_dir, storage_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logger.info(f"File uploaded: {file.filename} -> {analysis_id}")
        
        # 6. Create analysis record
        create_analysis(
            analysis_id=analysis_id,
            filename=file.filename,
            file_path=file_path,
            source="manual_upload"
        )
        
        # 7. Run analysis
        logger.info(f"Processing {safe_filename} with TCC engine...")
        engine = get_analysis_engine()
        results = engine.process_frame(file_path)
        
        # 8. Save results
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
        raise
    except (OSError, IOError, RuntimeError) as e:
        logger.error(f"Upload Error: {e}")
        if 'analysis_id' in locals():
            update_analysis_status(analysis_id, 'failed')
        raise HTTPException(status_code=500, detail=str(e))
