"""
File Utilities

Helper functions for file validation, sanitization, and handling.
"""

import os
import re
import uuid
from pathlib import Path
from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException, status
from core.database import get_connection
from config import settings


def validate_file_extension(filename: str) -> bool:
    """
    Check if file has an allowed extension.
    
    Args:
        filename: Name of the file
        
    Returns:
        True if extension is allowed, False otherwise
    """
    ext = Path(filename).suffix.lower()
    return ext in settings.ALLOWED_EXTENSIONS


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal and other attacks.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Get just the filename (no path)
    filename = os.path.basename(filename)
    
    # Remove any non-alphanumeric characters except dots, hyphens, underscores
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext
    
    return filename


def generate_unique_filename(original_filename: str) -> str:
    """
    Generate a unique filename using UUID.
    
    Args:
        original_filename: Original filename
        
    Returns:
        Unique filename with UUID prefix
    """
    sanitized = sanitize_filename(original_filename)
    ext = Path(sanitized).suffix
    unique_id = str(uuid.uuid4())
    return f"{unique_id}{ext}"


async def validate_upload_file(file: UploadFile) -> Tuple[str, str]:
    """
    Validate uploaded file (size, type, etc.).
    
    Args:
        file: Uploaded file from FastAPI
        
    Returns:
        Tuple of (original_filename, sanitized_filename)
        
    Raises:
        HTTPException: If validation fails
    """
    # Check if file exists
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    # Check filename
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename"
        )
    
    # Validate extension
    if not validate_file_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size (read first chunk to verify it's not empty)
    content = await file.read(1024)  # Read first 1KB
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty"
        )
    
    # Reset file pointer
    await file.seek(0)
    
    # Generate unique filename
    sanitized_filename = generate_unique_filename(file.filename)
    
    return file.filename, sanitized_filename


async def save_upload_file(
    file: UploadFile,
    destination: str,
    chunk_size: int = 1024 * 1024  # 1MB chunks
) -> int:
    """
    Save uploaded file to destination.
    
    Args:
        file: Uploaded file
        destination: Destination file path
        chunk_size: Size of chunks to read/write
        
    Returns:
        Total bytes written
        
    Raises:
        HTTPException: If save fails
    """
    try:
        total_size = 0
        
        # Ensure destination directory exists
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        # Write file in chunks
        with open(destination, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                
                total_size += len(chunk)
                
                # Check size limit
                if total_size > settings.MAX_UPLOAD_SIZE:
                    # Delete partial file
                    f.close()
                    os.remove(destination)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / (1024*1024):.0f}MB"
                    )
                
                f.write(chunk)
        
        return total_size
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up on error
        if os.path.exists(destination):
            os.remove(destination)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )


def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in MB
    """
    size_bytes = os.path.getsize(file_path)
    return size_bytes / (1024 * 1024)
