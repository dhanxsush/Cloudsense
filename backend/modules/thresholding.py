"""
Module 2: Physical Thresholding
Applies physics-based brightness temperature thresholding for cold cloud isolation.
"""

import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Physical thresholds based on meteorological research
BT_COLD_THRESHOLD = 218.0    # Kelvin - deep convective cloud tops
BT_WARM_THRESHOLD = 250.0    # Kelvin - general cloud detection
BT_CIRRUS_THRESHOLD = 230.0  # Kelvin - cirrus cloud detection


def apply_bt_threshold(bt_array: np.ndarray, 
                       threshold: float = BT_COLD_THRESHOLD) -> np.ndarray:
    """
    Apply brightness temperature threshold to isolate cold cloud tops.
    
    TCCs (Tropical Cloud Clusters) are characterized by very cold cloud tops
    (<218K) indicating deep convection reaching the upper troposphere.
    
    Args:
        bt_array: Brightness temperature array in Kelvin
        threshold: Temperature threshold in Kelvin (default 218K)
        
    Returns:
        Binary mask (uint8) where 1 = cold cloud, 0 = background
    """
    mask = (bt_array < threshold).astype(np.uint8)
    
    cold_pixels = np.sum(mask)
    total_pixels = mask.size
    coverage = (cold_pixels / total_pixels) * 100
    
    logger.debug(f"BT threshold {threshold}K: {cold_pixels} pixels ({coverage:.2f}% coverage)")
    
    return mask


def create_cold_cloud_mask(bt_array: np.ndarray,
                           primary_threshold: float = BT_COLD_THRESHOLD,
                           secondary_threshold: float = BT_WARM_THRESHOLD,
                           min_cold_fraction: float = 0.1) -> np.ndarray:
    """
    Create multi-level cold cloud mask with adaptive thresholding.
    
    Uses primary threshold (218K) for core convective regions,
    with optional secondary threshold for surrounding cloud areas.
    
    Args:
        bt_array: Brightness temperature array in Kelvin
        primary_threshold: Core convection threshold (default 218K)
        secondary_threshold: Extended cloud threshold (default 250K)
        min_cold_fraction: Minimum fraction of cold pixels required
        
    Returns:
        Binary mask with cold cloud regions marked as 1
    """
    # Primary mask: deep convection
    primary_mask = (bt_array < primary_threshold).astype(np.uint8)
    
    # Check if we have enough cold pixels
    cold_fraction = np.mean(primary_mask)
    
    if cold_fraction < min_cold_fraction:
        logger.info(f"Low cold cloud coverage ({cold_fraction:.2%}). Using secondary threshold.")
        # Use secondary threshold but weight primary regions
        secondary_mask = (bt_array < secondary_threshold).astype(np.uint8)
        return secondary_mask
    
    return primary_mask


def apply_morphological_cleanup(mask: np.ndarray,
                                 kernel_size: int = 3,
                                 iterations: int = 1) -> np.ndarray:
    """
    Clean up cloud mask using morphological operations.
    
    Removes small noise (opening) and fills small holes (closing).
    
    Args:
        mask: Binary cloud mask
        kernel_size: Size of morphological kernel
        iterations: Number of iterations for each operation
        
    Returns:
        Cleaned binary mask
    """
    import cv2
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    
    # Opening: erosion followed by dilation (removes small noise)
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=iterations)
    
    # Closing: dilation followed by erosion (fills small holes)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=iterations)
    
    return closed


def get_bt_statistics(bt_array: np.ndarray, 
                      mask: Optional[np.ndarray] = None) -> dict:
    """
    Compute brightness temperature statistics for the image or masked region.
    
    Args:
        bt_array: Brightness temperature array in Kelvin
        mask: Optional binary mask to restrict statistics
        
    Returns:
        Dictionary with min, max, mean, std of BT values
    """
    if mask is not None:
        values = bt_array[mask == 1]
    else:
        values = bt_array.flatten()
    
    if len(values) == 0:
        return {
            'min_bt': None,
            'max_bt': None,
            'mean_bt': None,
            'std_bt': None,
            'pixel_count': 0
        }
    
    return {
        'min_bt': float(np.min(values)),
        'max_bt': float(np.max(values)),
        'mean_bt': float(np.mean(values)),
        'std_bt': float(np.std(values)),
        'pixel_count': int(len(values))
    }


def estimate_convective_intensity(bt_array: np.ndarray, 
                                   mask: np.ndarray) -> str:
    """
    Estimate convective intensity based on minimum BT in cloud system.
    
    Classification based on meteorological standards:
    - Extreme: < 190K (overshooting tops)
    - Strong: 190-200K (intense convection)
    - Moderate: 200-210K (moderate convection)
    - Weak: 210-218K (weak convection)
    
    Args:
        bt_array: Brightness temperature array in Kelvin
        mask: Binary mask of cloud system
        
    Returns:
        Intensity classification string
    """
    if np.sum(mask) == 0:
        return "none"
    
    min_bt = np.min(bt_array[mask == 1])
    
    if min_bt < 190.0:
        return "extreme"
    elif min_bt < 200.0:
        return "strong"
    elif min_bt < 210.0:
        return "moderate"
    else:
        return "weak"
