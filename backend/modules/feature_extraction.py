"""
Module 6: Feature Extraction
Computes comprehensive cluster features for TCC analysis.
"""

import numpy as np
import cv2
from typing import Dict, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

# Physical constants
PIXEL_AREA_KM2 = 16.0  # 4km x 4km
EARTH_RADIUS_KM = 6371.0

# Cloud-top height estimation parameters (based on tropical atmosphere)
# Standard tropical lapse rate: ~6.5 K/km
TROPOPAUSE_HEIGHT_KM = 16.0  # Tropical tropopause height
TROPOPAUSE_TEMP_K = 190.0    # Approximate tropopause temperature
SURFACE_TEMP_K = 300.0       # Approximate surface temperature
SURFACE_HEIGHT_KM = 0.0


def compute_cluster_features(pixel_coords: np.ndarray,
                              bt_array: np.ndarray,
                              lat_grid: np.ndarray,
                              lon_grid: np.ndarray,
                              cluster_id: int = 0) -> Dict:
    """
    Compute comprehensive features for a cloud cluster.
    
    Args:
        pixel_coords: Array of (y, x) pixel coordinates (N, 2)
        bt_array: Brightness temperature array
        lat_grid: Latitude grid
        lon_grid: Longitude grid
        cluster_id: Cluster identifier
        
    Returns:
        Dictionary with all computed features
    """
    y_coords = pixel_coords[:, 0].astype(int)
    x_coords = pixel_coords[:, 1].astype(int)
    
    # Ensure within bounds
    H, W = bt_array.shape
    valid_mask = (y_coords >= 0) & (y_coords < H) & (x_coords >= 0) & (x_coords < W)
    y_coords = y_coords[valid_mask]
    x_coords = x_coords[valid_mask]
    
    if len(y_coords) == 0:
        return _empty_features(cluster_id)
    
    # Extract values at cluster pixels
    bt_values = bt_array[y_coords, x_coords]
    lat_values = lat_grid[y_coords, x_coords]
    lon_values = lon_grid[y_coords, x_coords]
    
    # Compute features
    features = {
        'cluster_id': cluster_id,
        
        # Geographic centroid
        'centroid_lat': float(np.mean(lat_values)),
        'centroid_lon': float(np.mean(lon_values)),
        
        # Pixel centroid
        'centroid_y': float(np.mean(y_coords)),
        'centroid_x': float(np.mean(x_coords)),
        
        # Size metrics
        'pixel_count': int(len(y_coords)),
        'area_km2': float(len(y_coords) * PIXEL_AREA_KM2),
        'radius_km': float(np.sqrt(len(y_coords) * PIXEL_AREA_KM2 / np.pi)),
        
        # BT statistics
        'min_bt': float(np.min(bt_values)),
        'max_bt': float(np.max(bt_values)),
        'mean_bt': float(np.mean(bt_values)),
        'std_bt': float(np.std(bt_values)),
        
        # Cloud-top height estimate
        'cloud_top_height_km': estimate_cloud_top_height(float(np.min(bt_values))),
        
        # Shape metrics
        **_compute_shape_metrics(y_coords, x_coords),
        
        # Geographic extent
        **_compute_geographic_extent(lat_values, lon_values),
        
        # Intensity classification
        'intensity': _classify_intensity(float(np.min(bt_values))),
    }
    
    return features


def _empty_features(cluster_id: int) -> Dict:
    """Return empty feature dictionary for invalid clusters."""
    return {
        'cluster_id': cluster_id,
        'centroid_lat': None,
        'centroid_lon': None,
        'centroid_y': None,
        'centroid_x': None,
        'pixel_count': 0,
        'area_km2': 0.0,
        'radius_km': 0.0,
        'min_bt': None,
        'max_bt': None,
        'mean_bt': None,
        'std_bt': None,
        'cloud_top_height_km': None,
        'aspect_ratio': None,
        'orientation_deg': None,
        'eccentricity': None,
        'lat_extent': None,
        'lon_extent': None,
        'intensity': 'none',
    }


def estimate_cloud_top_height(min_bt: float) -> float:
    """
    Estimate cloud-top height from minimum brightness temperature.
    
    Uses linear interpolation based on tropical atmospheric profile.
    Assumes standard lapse rate from surface to tropopause.
    
    Args:
        min_bt: Minimum brightness temperature in Kelvin
        
    Returns:
        Estimated cloud-top height in km
    """
    if min_bt >= SURFACE_TEMP_K:
        return SURFACE_HEIGHT_KM
    
    if min_bt <= TROPOPAUSE_TEMP_K:
        return TROPOPAUSE_HEIGHT_KM
    
    # Linear interpolation
    temp_fraction = (SURFACE_TEMP_K - min_bt) / (SURFACE_TEMP_K - TROPOPAUSE_TEMP_K)
    height = SURFACE_HEIGHT_KM + temp_fraction * (TROPOPAUSE_HEIGHT_KM - SURFACE_HEIGHT_KM)
    
    return float(height)


def _compute_shape_metrics(y_coords: np.ndarray, 
                           x_coords: np.ndarray) -> Dict:
    """
    Compute shape metrics using ellipse fitting.
    
    - Aspect ratio: major axis / minor axis
    - Orientation: angle of major axis in degrees
    - Eccentricity: measure of elongation (0 = circle, 1 = line)
    """
    if len(y_coords) < 5:
        return {
            'aspect_ratio': 1.0,
            'orientation_deg': 0.0,
            'eccentricity': 0.0
        }
    
    try:
        # Prepare points for ellipse fitting
        points = np.column_stack((x_coords, y_coords)).astype(np.float32)
        
        # Fit ellipse
        (center_x, center_y), (minor_axis, major_axis), angle = cv2.fitEllipse(points)
        
        # Ensure major >= minor
        if minor_axis > major_axis:
            major_axis, minor_axis = minor_axis, major_axis
            angle = (angle + 90) % 180
        
        # Compute metrics
        aspect_ratio = major_axis / max(minor_axis, 1e-6)
        
        # Eccentricity: sqrt(1 - (b/a)^2)
        eccentricity = np.sqrt(1 - (minor_axis / max(major_axis, 1e-6)) ** 2)
        
        return {
            'aspect_ratio': float(aspect_ratio),
            'orientation_deg': float(angle),
            'eccentricity': float(eccentricity)
        }
        
    except cv2.error:
        logger.warning("Ellipse fitting failed, using default shape metrics")
        return {
            'aspect_ratio': 1.0,
            'orientation_deg': 0.0,
            'eccentricity': 0.0
        }


def _compute_geographic_extent(lat_values: np.ndarray, 
                               lon_values: np.ndarray) -> Dict:
    """Compute geographic extent of the cluster."""
    return {
        'lat_extent': float(np.max(lat_values) - np.min(lat_values)),
        'lon_extent': float(np.max(lon_values) - np.min(lon_values)),
        'lat_min': float(np.min(lat_values)),
        'lat_max': float(np.max(lat_values)),
        'lon_min': float(np.min(lon_values)),
        'lon_max': float(np.max(lon_values)),
    }


def _classify_intensity(min_bt: float) -> str:
    """
    Classify convective intensity based on minimum BT.
    
    Categories based on meteorological standards:
    - extreme: < 190K (overshooting tops)
    - strong: 190-200K (intense deep convection)
    - moderate: 200-210K (moderate convection)
    - weak: 210-218K (weak convection)
    - none: >= 218K (not convective)
    """
    if min_bt < 190.0:
        return "extreme"
    elif min_bt < 200.0:
        return "strong"
    elif min_bt < 210.0:
        return "moderate"
    elif min_bt < 218.0:
        return "weak"
    else:
        return "none"


def compute_cluster_evolution(current_features: Dict,
                               previous_features: Dict,
                               time_delta_hours: float) -> Dict:
    """
    Compute evolution metrics between two time steps.
    
    Args:
        current_features: Features at current time
        previous_features: Features at previous time
        time_delta_hours: Time difference in hours
        
    Returns:
        Dictionary with evolution metrics
    """
    if not previous_features or not current_features:
        return {}
    
    # Area change rate (km²/hour)
    area_change = current_features['area_km2'] - previous_features['area_km2']
    area_rate = area_change / max(time_delta_hours, 0.01)
    
    # BT change (intensification indicator)
    bt_change = current_features['mean_bt'] - previous_features['mean_bt']
    
    # Movement speed (km/hour)
    lat_diff = current_features['centroid_lat'] - previous_features['centroid_lat']
    lon_diff = current_features['centroid_lon'] - previous_features['centroid_lon']
    distance_km = _haversine_distance(
        previous_features['centroid_lat'], previous_features['centroid_lon'],
        current_features['centroid_lat'], current_features['centroid_lon']
    )
    speed_kmh = distance_km / max(time_delta_hours, 0.01)
    
    # Movement direction (degrees, north = 0)
    direction = np.degrees(np.arctan2(lon_diff, lat_diff)) % 360
    
    return {
        'area_change_rate_km2h': float(area_rate),
        'bt_change_per_hour': float(bt_change / max(time_delta_hours, 0.01)),
        'movement_speed_kmh': float(speed_kmh),
        'movement_direction_deg': float(direction),
        'is_intensifying': bt_change < 0,  # Colder = more intense
        'is_expanding': area_change > 0,
    }


def _haversine_distance(lat1: float, lon1: float, 
                        lat2: float, lon2: float) -> float:
    """Calculate great-circle distance in km."""
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    
    a = np.sin(dlat / 2) ** 2 + \
        np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    return EARTH_RADIUS_KM * c


def features_to_dict(features: Dict) -> Dict:
    """Convert features to JSON-serializable dictionary."""
    result = {}
    for key, value in features.items():
        if isinstance(value, (np.floating, np.integer)):
            result[key] = float(value)
        elif isinstance(value, np.ndarray):
            result[key] = value.tolist()
        else:
            result[key] = value
    return result
