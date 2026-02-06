"""
Module 4: Pseudo-Label Generation
Generates training masks from validated DBSCAN clusters (self-supervised approach).
"""

import os
import json
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Import cluster type
from .clustering import CloudCluster


def generate_pseudo_labels(clusters: List[CloudCluster],
                            shape: Tuple[int, int]) -> np.ndarray:
    """
    Generate binary pseudo-label mask from validated clusters.
    
    This is the key self-supervised step: validated DBSCAN clusters
    become training labels for the U-Net model.
    
    Args:
        clusters: List of validated CloudCluster objects
        shape: Output mask shape (H, W)
        
    Returns:
        Binary mask (uint8) where 1 = TCC region, 0 = background
    """
    mask = np.zeros(shape, dtype=np.uint8)
    
    for cluster in clusters:
        y_coords = cluster.pixel_coords[:, 0].astype(int)
        x_coords = cluster.pixel_coords[:, 1].astype(int)
        
        # Ensure coordinates are within bounds
        valid_mask = (
            (y_coords >= 0) & (y_coords < shape[0]) &
            (x_coords >= 0) & (x_coords < shape[1])
        )
        
        mask[y_coords[valid_mask], x_coords[valid_mask]] = 1
    
    logger.debug(f"Generated pseudo-label with {np.sum(mask)} positive pixels from {len(clusters)} clusters")
    return mask


def save_mask(mask: np.ndarray, output_path: str) -> str:
    """
    Save binary mask as NumPy file.
    
    Args:
        mask: Binary mask array
        output_path: Output file path (.npy)
        
    Returns:
        Absolute path to saved file
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    np.save(output_path, mask)
    logger.debug(f"Saved mask to {output_path}")
    return os.path.abspath(output_path)


def load_mask(mask_path: str) -> np.ndarray:
    """
    Load binary mask from NumPy file.
    
    Args:
        mask_path: Path to .npy file
        
    Returns:
        Binary mask array
    """
    return np.load(mask_path)


def create_dataset_index(h5_dir: str,
                          mask_dir: str,
                          output_path: str,
                          recursive: bool = True) -> List[Dict]:
    """
    Create dataset index linking H5 files to their pseudo-label masks.
    
    Args:
        h5_dir: Directory containing H5 files
        mask_dir: Directory containing mask files
        output_path: Output JSON file path
        recursive: Whether to search subdirectories
        
    Returns:
        List of dataset entries with h5_path, mask_path, timestamp
    """
    from .preprocessing import extract_timestamp_string
    
    entries = []
    
    # Find all H5 files
    if recursive:
        for root, dirs, files in os.walk(h5_dir):
            for f in files:
                if f.endswith('.h5'):
                    h5_path = os.path.join(root, f)
                    entry = _create_index_entry(h5_path, mask_dir)
                    if entry:
                        entries.append(entry)
    else:
        for f in os.listdir(h5_dir):
            if f.endswith('.h5'):
                h5_path = os.path.join(h5_dir, f)
                entry = _create_index_entry(h5_path, mask_dir)
                if entry:
                    entries.append(entry)
    
    # Sort by timestamp
    entries.sort(key=lambda x: x['timestamp'])
    
    # Save index
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(entries, f, indent=2)
    
    logger.info(f"Created dataset index with {len(entries)} entries at {output_path}")
    return entries


def _create_index_entry(h5_path: str, mask_dir: str) -> Optional[Dict]:
    """Create a single dataset index entry."""
    from .preprocessing import extract_timestamp_string
    
    timestamp = extract_timestamp_string(h5_path)
    mask_filename = f"{timestamp}.npy"
    mask_path = os.path.join(mask_dir, mask_filename)
    
    entry = {
        'h5_path': os.path.abspath(h5_path),
        'timestamp': timestamp,
        'mask_path': os.path.abspath(mask_path) if os.path.exists(mask_path) else None,
        'has_mask': os.path.exists(mask_path)
    }
    
    return entry


def generate_labels_for_directory(h5_dir: str,
                                   mask_dir: str,
                                   bt_threshold: float = 218.0,
                                   min_area_km2: float = 34800.0) -> List[Dict]:
    """
    Generate pseudo-labels for all H5 files in a directory.
    
    Complete pipeline: H5 → Threshold → DBSCAN → Validate → Mask
    
    Args:
        h5_dir: Directory with H5 files
        mask_dir: Output directory for masks
        bt_threshold: BT threshold for cold cloud detection
        min_area_km2: Minimum cluster area
        
    Returns:
        List of entries with generation results
    """
    from .preprocessing import load_h5_file, extract_timestamp_string
    from .thresholding import apply_bt_threshold
    from .clustering import cluster_clouds, apply_geophysical_constraints
    
    os.makedirs(mask_dir, exist_ok=True)
    
    results = []
    h5_files = []
    
    # Collect all H5 files
    for root, dirs, files in os.walk(h5_dir):
        for f in files:
            if f.endswith('.h5'):
                h5_files.append(os.path.join(root, f))
    
    h5_files.sort()
    logger.info(f"Processing {len(h5_files)} H5 files for pseudo-label generation")
    
    for h5_path in h5_files:
        result = _process_single_file(h5_path, mask_dir, bt_threshold, min_area_km2)
        results.append(result)
    
    # Summary statistics
    with_tcc = sum(1 for r in results if r.get('has_tcc', False))
    logger.info(f"Pseudo-label generation complete: {with_tcc}/{len(results)} files have TCC detections")
    
    return results


def _process_single_file(h5_path: str,
                          mask_dir: str,
                          bt_threshold: float,
                          min_area_km2: float) -> Dict:
    """Process a single H5 file and generate pseudo-label mask."""
    from .preprocessing import load_h5_file, extract_timestamp_string
    from .thresholding import apply_bt_threshold
    from .clustering import cluster_clouds, apply_geophysical_constraints
    
    timestamp = extract_timestamp_string(h5_path)
    
    try:
        # Load data
        bt_array, lat_grid, lon_grid = load_h5_file(h5_path)
        
        # Apply BT threshold
        cloud_mask = apply_bt_threshold(bt_array, bt_threshold)
        
        # Cluster
        clusters = cluster_clouds(cloud_mask, lat_grid, lon_grid)
        
        # Apply geophysical constraints
        valid_clusters = apply_geophysical_constraints(clusters, min_area_km2=min_area_km2)
        
        # Generate pseudo-label
        pseudo_label = generate_pseudo_labels(valid_clusters, bt_array.shape)
        
        # Save mask
        mask_path = os.path.join(mask_dir, f"{timestamp}.npy")
        save_mask(pseudo_label, mask_path)
        
        has_tcc = len(valid_clusters) > 0
        
        return {
            'h5_path': os.path.abspath(h5_path),
            'mask_path': os.path.abspath(mask_path),
            'timestamp': timestamp,
            'has_tcc': has_tcc,
            'cluster_count': len(valid_clusters),
            'total_tcc_pixels': int(np.sum(pseudo_label))
        }
        
    except Exception as e:
        logger.error(f"Error processing {h5_path}: {e}")
        return {
            'h5_path': os.path.abspath(h5_path),
            'timestamp': timestamp,
            'error': str(e),
            'has_tcc': False
        }


def visualize_pseudo_label(bt_array: np.ndarray,
                            mask: np.ndarray,
                            output_path: str,
                            title: str = "TCC Pseudo-Label") -> str:
    """
    Create visualization comparing BT image and pseudo-label mask.
    
    Args:
        bt_array: Brightness temperature array
        mask: Binary pseudo-label mask
        output_path: Output image path (.png)
        title: Plot title
        
    Returns:
        Path to saved visualization
    """
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # BT image
    im1 = axes[0].imshow(bt_array, cmap='jet_r', vmin=180, vmax=320)
    axes[0].set_title(f"IR Brightness Temperature\n{title}")
    plt.colorbar(im1, ax=axes[0], label='Temperature (K)')
    
    # Pseudo-label mask
    axes[1].imshow(mask, cmap='gray')
    pixel_count = np.sum(mask)
    area_km2 = pixel_count * 16  # 4km x 4km pixels
    axes[1].set_title(f"TCC Pseudo-Label\n{pixel_count} pixels ({area_km2:,.0f} km²)")
    
    plt.tight_layout()
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return output_path
