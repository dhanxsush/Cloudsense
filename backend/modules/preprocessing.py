"""
Module 1: Input & Pre-processing
Handles H5 file loading, BT extraction, normalization, and geolocation.
"""

import os
import re
import h5py
import numpy as np
import cv2
from datetime import datetime
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Physical constants
BT_MIN = 180.0  # Kelvin - minimum expected brightness temperature
BT_MAX = 320.0  # Kelvin - maximum expected brightness temperature
PIXEL_RESOLUTION_KM = 4.0  # km per pixel (INSAT-3D resolution)

# Default geolocation bounds (Indian Ocean / Bay of Bengal region)
DEFAULT_LAT_RANGE = (0.0, 30.0)   # 0°N to 30°N
DEFAULT_LON_RANGE = (60.0, 100.0)  # 60°E to 100°E


def load_h5_file(h5_path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Load INSAT-3D H5 file and extract calibrated BT data with geolocation.
    
    Args:
        h5_path: Path to the .h5 file
        
    Returns:
        Tuple of (bt_array, lat_grid, lon_grid)
        - bt_array: Brightness temperature in Kelvin (H, W)
        - lat_grid: Latitude values (H, W)
        - lon_grid: Longitude values (H, W)
        
    Raises:
        FileNotFoundError: If H5 file doesn't exist
        KeyError: If required datasets are missing
    """
    if not os.path.exists(h5_path):
        raise FileNotFoundError(f"H5 file not found: {h5_path}")
    
    with h5py.File(h5_path, 'r') as f:
        # Extract raw counts and LUT for TIR1 band
        if 'IMG_TIR1' not in f:
            raise KeyError("IMG_TIR1 dataset not found in H5 file")
        
        raw_counts = f['IMG_TIR1'][0]  # Shape: (H, W)
        
        if 'IMG_TIR1_TEMP' not in f:
            raise KeyError("IMG_TIR1_TEMP LUT not found in H5 file")
        
        lut = f['IMG_TIR1_TEMP'][:]
        
        # Calibrate: convert counts to brightness temperature using LUT
        bt_array = lut[raw_counts].astype(np.float32)
        
        # Extract geolocation data
        lat_grid, lon_grid = _extract_geolocation(f, bt_array.shape)
    
    logger.info(f"Loaded H5 file: {h5_path}, shape: {bt_array.shape}")
    return bt_array, lat_grid, lon_grid


def _extract_geolocation(f: h5py.File, shape: Tuple[int, int]) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract latitude and longitude grids from H5 file.
    Falls back to estimated grid if not available.
    """
    H, W = shape
    
    try:
        lat_grid = f['Latitude'][:]
        lon_grid = f['Longitude'][:]
        
        # Validate shape matches
        if lat_grid.shape != shape or lon_grid.shape != shape:
            logger.warning(f"Geolocation shape mismatch. Expected {shape}, got lat:{lat_grid.shape}, lon:{lon_grid.shape}")
            raise ValueError("Shape mismatch")
            
    except (KeyError, ValueError) as e:
        logger.warning(f"Geolocation data unavailable ({e}). Using estimated Indian Ocean coordinates.")
        lat_grid, lon_grid = _create_fallback_geolocation(H, W)
    
    return lat_grid.astype(np.float32), lon_grid.astype(np.float32)


def _create_fallback_geolocation(H: int, W: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create estimated geolocation grid for Indian Ocean / Bay of Bengal region.
    Used when actual geolocation data is not available in H5 file.
    """
    lat_min, lat_max = DEFAULT_LAT_RANGE
    lon_min, lon_max = DEFAULT_LON_RANGE
    
    lat_1d = np.linspace(lat_max, lat_min, H)  # North to South
    lon_1d = np.linspace(lon_min, lon_max, W)  # West to East
    
    lon_grid, lat_grid = np.meshgrid(lon_1d, lat_1d)
    
    return lat_grid.astype(np.float32), lon_grid.astype(np.float32)


def normalize_bt(bt_array: np.ndarray, 
                 min_bt: float = BT_MIN, 
                 max_bt: float = BT_MAX) -> np.ndarray:
    """
    Normalize brightness temperature to [0, 1] range.
    
    Uses physics-based bounds (180K-320K) for consistent normalization
    across different satellite images.
    
    Args:
        bt_array: Raw brightness temperature in Kelvin
        min_bt: Minimum BT for normalization (default 180K)
        max_bt: Maximum BT for normalization (default 320K)
        
    Returns:
        Normalized array in [0, 1] range
    """
    normalized = (bt_array - min_bt) / (max_bt - min_bt)
    return np.clip(normalized, 0.0, 1.0).astype(np.float32)


def resize_for_model(array: np.ndarray, 
                     target_size: int = 512,
                     interpolation: int = cv2.INTER_LINEAR) -> np.ndarray:
    """
    Resize array to target dimensions for model input.
    
    Args:
        array: Input array (H, W) or (H, W, C)
        target_size: Target dimension (will be square)
        interpolation: OpenCV interpolation method
        
    Returns:
        Resized array (target_size, target_size) or (target_size, target_size, C)
    """
    return cv2.resize(array, (target_size, target_size), interpolation=interpolation)


def resize_mask_to_original(mask: np.ndarray, 
                            original_shape: Tuple[int, int]) -> np.ndarray:
    """
    Resize binary mask back to original image dimensions.
    
    Args:
        mask: Binary mask from model (usually 512x512)
        original_shape: Original (H, W) dimensions
        
    Returns:
        Resized mask matching original dimensions
    """
    return cv2.resize(mask, (original_shape[1], original_shape[0]), 
                      interpolation=cv2.INTER_NEAREST)


def extract_timestamp(filename: str) -> Optional[datetime]:
    """
    Extract timestamp from INSAT-3D filename.
    
    Expected format: 3RIMG_DDMMMYYYY_HHMM_L1C_ASIA_MER_V01R00.h5
    Example: 3RIMG_30NOV2023_0045_L1C_ASIA_MER_V01R00.h5
    
    Args:
        filename: H5 filename (basename or full path)
        
    Returns:
        datetime object or None if parsing fails
    """
    basename = os.path.basename(filename)
    
    # Pattern: 3RIMG_DDMMMYYYY_HHMM
    pattern = r'3RIMG_(\d{2})([A-Z]{3})(\d{4})_(\d{4})'
    match = re.search(pattern, basename)
    
    if not match:
        logger.warning(f"Could not parse timestamp from filename: {basename}")
        return None
    
    day, month_str, year, time_str = match.groups()
    
    # Convert month abbreviation to number
    months = {
        'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
        'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
    }
    
    try:
        month = months[month_str.upper()]
        hour = int(time_str[:2])
        minute = int(time_str[2:])
        
        return datetime(int(year), month, int(day), hour, minute)
    except (KeyError, ValueError) as e:
        logger.warning(f"Error parsing timestamp from {basename}: {e}")
        return None


def extract_timestamp_string(filename: str) -> str:
    """
    Extract timestamp as string for use in tracking.
    Returns filename part if full parsing fails.
    """
    dt = extract_timestamp(filename)
    if dt:
        return dt.strftime("%Y%m%d_%H%M")
    
    # Fallback: extract date_time portion from filename
    basename = os.path.basename(filename)
    parts = basename.split('_')
    if len(parts) >= 3:
        return f"{parts[1]}_{parts[2]}"
    return basename


def get_pixel_area_km2() -> float:
    """Return pixel area in km² for INSAT-3D resolution."""
    return PIXEL_RESOLUTION_KM ** 2  # 16 km²
