"""
Module 3: Clustering
GPU-accelerated DBSCAN clustering with geophysical constraints for TCC detection.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Geophysical constraints from meteorological research
MIN_AREA_KM2 = 34800.0        # Minimum TCC area (34,800 km²)
MIN_RADIUS_KM = 111.0          # Minimum equivalent radius (111 km)
MIN_CENTROID_SEPARATION_KM = 1200.0  # Minimum separation between TCC centroids

# DBSCAN parameters
DBSCAN_EPS_PIXELS = 1.5        # Connectivity distance in pixels
DBSCAN_MIN_SAMPLES = 5         # Minimum pixels to form core point
PIXEL_AREA_KM2 = 16.0          # 4km x 4km pixel resolution

# Check for GPU availability
try:
    from cuml.cluster import DBSCAN as cuDBSCAN
    GPU_AVAILABLE = True
    logger.info("cuML GPU acceleration available for DBSCAN")
except ImportError:
    GPU_AVAILABLE = False
    logger.info("cuML not available, using scikit-learn DBSCAN (CPU)")


@dataclass
class CloudCluster:
    """Represents a detected cloud cluster with its properties."""
    cluster_id: int
    pixel_coords: np.ndarray  # (N, 2) array of (y, x) coordinates
    centroid_pixel: Tuple[float, float]  # (y, x) centroid in pixel space
    centroid_lat: float
    centroid_lon: float
    area_km2: float
    radius_km: float
    pixel_count: int


def cluster_clouds(mask: np.ndarray,
                   lat_grid: np.ndarray,
                   lon_grid: np.ndarray,
                   use_gpu: bool = False,
                   eps: float = DBSCAN_EPS_PIXELS,
                   min_samples: int = DBSCAN_MIN_SAMPLES) -> List[CloudCluster]:
    """
    Cluster cold cloud pixels using DBSCAN algorithm.
    
    Args:
        mask: Binary cloud mask (H, W) where 1 = cloud pixel
        lat_grid: Latitude values (H, W)
        lon_grid: Longitude values (H, W)
        use_gpu: Whether to use GPU acceleration (requires cuML)
        eps: DBSCAN neighborhood distance in pixels
        min_samples: Minimum pixels to form a cluster core
        
    Returns:
        List of CloudCluster objects with cluster properties
    """
    # Extract cloud pixel coordinates
    y_coords, x_coords = np.where(mask == 1)
    
    if len(y_coords) == 0:
        logger.debug("No cloud pixels found in mask")
        return []
    
    # Stack coordinates for clustering
    coords = np.column_stack((y_coords, x_coords)).astype(np.float32)
    
    # Perform DBSCAN clustering
    if use_gpu and GPU_AVAILABLE:
        labels = _dbscan_gpu(coords, eps, min_samples)
    else:
        labels = _dbscan_cpu(coords, eps, min_samples)
    
    # Extract clusters (excluding noise label -1)
    unique_labels = set(labels)
    unique_labels.discard(-1)
    
    clusters = []
    for cluster_id in unique_labels:
        cluster_mask = (labels == cluster_id)
        cluster_coords = coords[cluster_mask]
        
        cluster = _create_cluster(
            cluster_id=int(cluster_id),
            coords=cluster_coords,
            y_coords=y_coords[cluster_mask],
            x_coords=x_coords[cluster_mask],
            lat_grid=lat_grid,
            lon_grid=lon_grid
        )
        clusters.append(cluster)
    
    logger.info(f"DBSCAN found {len(clusters)} clusters from {len(y_coords)} cloud pixels")
    return clusters


def _dbscan_cpu(coords: np.ndarray, eps: float, min_samples: int) -> np.ndarray:
    """Run DBSCAN using scikit-learn (CPU)."""
    from sklearn.cluster import DBSCAN
    
    db = DBSCAN(eps=eps, min_samples=min_samples, metric='euclidean', n_jobs=-1)
    return db.fit_predict(coords)


def _dbscan_gpu(coords: np.ndarray, eps: float, min_samples: int) -> np.ndarray:
    """Run DBSCAN using cuML (GPU)."""
    import cupy as cp
    
    coords_gpu = cp.asarray(coords)
    db = cuDBSCAN(eps=eps, min_samples=min_samples, metric='euclidean')
    labels_gpu = db.fit_predict(coords_gpu)
    
    return cp.asnumpy(labels_gpu)


def _create_cluster(cluster_id: int,
                    coords: np.ndarray,
                    y_coords: np.ndarray,
                    x_coords: np.ndarray,
                    lat_grid: np.ndarray,
                    lon_grid: np.ndarray) -> CloudCluster:
    """Create a CloudCluster object from pixel coordinates."""
    # Pixel centroid
    centroid_y = float(np.mean(y_coords))
    centroid_x = float(np.mean(x_coords))
    
    # Geographic centroid
    centroid_lat = float(np.mean(lat_grid[y_coords, x_coords]))
    centroid_lon = float(np.mean(lon_grid[y_coords, x_coords]))
    
    # Area and radius
    pixel_count = len(coords)
    area_km2 = pixel_count * PIXEL_AREA_KM2
    radius_km = np.sqrt(area_km2 / np.pi)
    
    return CloudCluster(
        cluster_id=cluster_id,
        pixel_coords=coords,
        centroid_pixel=(centroid_y, centroid_x),
        centroid_lat=centroid_lat,
        centroid_lon=centroid_lon,
        area_km2=area_km2,
        radius_km=radius_km,
        pixel_count=pixel_count
    )


def apply_geophysical_constraints(clusters: List[CloudCluster],
                                   min_area_km2: float = MIN_AREA_KM2,
                                   min_radius_km: float = MIN_RADIUS_KM,
                                   min_separation_km: float = MIN_CENTROID_SEPARATION_KM) -> List[CloudCluster]:
    """
    Filter clusters based on geophysical constraints.
    
    Constraints:
    - Minimum area >= 34,800 km²
    - Minimum radius >= 111 km
    - Minimum centroid separation >= 1,200 km (merges nearby clusters)
    
    Args:
        clusters: List of detected cloud clusters
        min_area_km2: Minimum area threshold in km²
        min_radius_km: Minimum equivalent radius in km
        min_separation_km: Minimum separation between centroids
        
    Returns:
        Filtered list of clusters meeting all constraints
    """
    if not clusters:
        return []
    
    # Step 1: Filter by area and radius
    filtered = [
        c for c in clusters
        if c.area_km2 >= min_area_km2 and c.radius_km >= min_radius_km
    ]
    
    initial_count = len(clusters)
    after_area_filter = len(filtered)
    
    logger.debug(f"Area/radius filter: {initial_count} -> {after_area_filter} clusters")
    
    if len(filtered) <= 1:
        return filtered
    
    # Step 2: Merge or filter clusters that are too close
    filtered = _apply_separation_constraint(filtered, min_separation_km)
    
    logger.info(f"Geophysical constraints: {initial_count} -> {len(filtered)} clusters")
    return filtered


def _apply_separation_constraint(clusters: List[CloudCluster],
                                  min_separation_km: float) -> List[CloudCluster]:
    """
    Apply minimum centroid separation constraint.
    Keeps the larger cluster when two are too close.
    """
    # Sort by area (largest first)
    sorted_clusters = sorted(clusters, key=lambda c: c.area_km2, reverse=True)
    
    result = []
    for cluster in sorted_clusters:
        is_valid = True
        for existing in result:
            distance = _haversine_distance(
                cluster.centroid_lat, cluster.centroid_lon,
                existing.centroid_lat, existing.centroid_lon
            )
            if distance < min_separation_km:
                is_valid = False
                break
        
        if is_valid:
            result.append(cluster)
    
    return result


def _haversine_distance(lat1: float, lon1: float, 
                        lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points in km.
    
    Uses Haversine formula for accuracy on spherical Earth.
    """
    R = 6371.0  # Earth radius in km
    
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    
    a = np.sin(dlat / 2) ** 2 + \
        np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    return R * c


def get_cluster_as_dict(cluster: CloudCluster) -> Dict:
    """Convert CloudCluster to dictionary for JSON serialization."""
    return {
        'cluster_id': cluster.cluster_id,
        'centroid_lat': cluster.centroid_lat,
        'centroid_lon': cluster.centroid_lon,
        'centroid_y': cluster.centroid_pixel[0],
        'centroid_x': cluster.centroid_pixel[1],
        'area_km2': cluster.area_km2,
        'radius_km': cluster.radius_km,
        'pixel_count': cluster.pixel_count
    }
