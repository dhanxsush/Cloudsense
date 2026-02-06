"""
Module 8: Output Generation
NetCDF, CSV, and JSON export for TCC analysis results.
"""

import os
import json
import csv
from datetime import datetime
from typing import List, Dict, Optional, Any
import numpy as np
import logging

logger = logging.getLogger(__name__)


def export_to_netcdf(trajectory_data: List[Dict],
                      metadata: Dict,
                      output_path: str) -> str:
    """
    Export trajectory data to CF-compliant NetCDF format.
    
    NetCDF is the standard format for meteorological data,
    compatible with climate research tools and forecast systems.
    
    Args:
        trajectory_data: List of tracked cluster dictionaries
        metadata: Analysis metadata (source, date range, etc.)
        output_path: Output .nc file path
        
    Returns:
        Absolute path to created file
    """
    try:
        from netCDF4 import Dataset
    except ImportError:
        raise ImportError("netCDF4 required for NetCDF export: pip install netCDF4")
    
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Create NetCDF file
    with Dataset(output_path, 'w', format='NETCDF4') as nc:
        # Global attributes (CF conventions)
        nc.Conventions = 'CF-1.8'
        nc.title = 'Tropical Cloud Cluster (TCC) Detection Results'
        nc.institution = 'CloudSense TCC Detection System'
        nc.source = metadata.get('source', 'INSAT-3D')
        nc.history = f"Created {datetime.utcnow().isoformat()} by CloudSense"
        nc.references = 'U-Net TCC Detection with Kalman Tracking'
        
        if not trajectory_data:
            logger.warning("No trajectory data to export")
            return os.path.abspath(output_path)
        
        # Determine dimensions
        n_obs = len(trajectory_data)
        
        # Create dimensions
        nc.createDimension('obs', n_obs)
        nc.createDimension('string_len', 32)
        
        # Create variables
        # Time/Track info
        track_id = nc.createVariable('track_id', 'i4', ('obs',))
        track_id.long_name = 'Track identifier'
        
        timestamp = nc.createVariable('timestamp', 'S1', ('obs', 'string_len'))
        timestamp.long_name = 'Observation timestamp'
        
        # Position
        lat = nc.createVariable('centroid_lat', 'f4', ('obs',))
        lat.units = 'degrees_north'
        lat.long_name = 'Cluster centroid latitude'
        lat.standard_name = 'latitude'
        
        lon = nc.createVariable('centroid_lon', 'f4', ('obs',))
        lon.units = 'degrees_east'
        lon.long_name = 'Cluster centroid longitude'
        lon.standard_name = 'longitude'
        
        # Size metrics
        area = nc.createVariable('area_km2', 'f4', ('obs',))
        area.units = 'km2'
        area.long_name = 'Cluster area'
        
        radius = nc.createVariable('radius_km', 'f4', ('obs',))
        radius.units = 'km'
        radius.long_name = 'Equivalent radius'
        
        # BT metrics
        mean_bt = nc.createVariable('mean_bt', 'f4', ('obs',))
        mean_bt.units = 'K'
        mean_bt.long_name = 'Mean brightness temperature'
        mean_bt.standard_name = 'brightness_temperature'
        
        min_bt = nc.createVariable('min_bt', 'f4', ('obs',))
        min_bt.units = 'K'
        min_bt.long_name = 'Minimum brightness temperature'
        
        # Cloud height
        cloud_top = nc.createVariable('cloud_top_height', 'f4', ('obs',))
        cloud_top.units = 'km'
        cloud_top.long_name = 'Estimated cloud top height'
        
        # Predicted flag
        is_pred = nc.createVariable('is_predicted', 'i1', ('obs',))
        is_pred.long_name = 'Whether position is Kalman prediction'
        
        # Write data
        for i, obs in enumerate(trajectory_data):
            track_id[i] = obs.get('track_id', 0)
            
            ts_str = str(obs.get('timestamp', ''))[:32]
            timestamp[i] = list(ts_str.ljust(32))
            
            lat[i] = obs.get('centroid_lat', np.nan)
            lon[i] = obs.get('centroid_lon', np.nan)
            area[i] = obs.get('area_km2', np.nan)
            radius[i] = obs.get('radius_km', np.nan)
            mean_bt[i] = obs.get('mean_bt', np.nan)
            min_bt[i] = obs.get('min_bt', np.nan)
            cloud_top[i] = obs.get('cloud_top_height_km', np.nan)
            is_pred[i] = 1 if obs.get('is_predicted', False) else 0
    
    logger.info(f"Exported {n_obs} observations to NetCDF: {output_path}")
    return os.path.abspath(output_path)


def export_to_csv(trajectory_data: List[Dict],
                   output_path: str,
                   include_all_fields: bool = True) -> str:
    """
    Export trajectory data to CSV format.
    
    Args:
        trajectory_data: List of tracked cluster dictionaries
        output_path: Output .csv file path
        include_all_fields: Whether to include all available fields
        
    Returns:
        Absolute path to created file
    """
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    if not trajectory_data:
        logger.warning("No trajectory data to export")
        # Create empty file with headers
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['track_id', 'timestamp', 'centroid_lat', 'centroid_lon',
                           'area_km2', 'radius_km', 'mean_bt', 'min_bt'])
        return os.path.abspath(output_path)
    
    # Determine all fields
    if include_all_fields:
        all_keys = set()
        for obs in trajectory_data:
            all_keys.update(obs.keys())
        
        # Order fields logically
        priority_fields = ['track_id', 'timestamp', 'centroid_lat', 'centroid_lon',
                          'area_km2', 'radius_km', 'mean_bt', 'min_bt', 'max_bt',
                          'cloud_top_height_km', 'intensity', 'is_predicted']
        
        fields = [f for f in priority_fields if f in all_keys]
        fields += sorted(all_keys - set(fields))
    else:
        fields = ['track_id', 'timestamp', 'centroid_lat', 'centroid_lon',
                 'area_km2', 'radius_km', 'mean_bt', 'min_bt']
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        
        for obs in trajectory_data:
            # Convert numpy types to Python types
            row = {k: _to_python_type(v) for k, v in obs.items()}
            writer.writerow(row)
    
    logger.info(f"Exported {len(trajectory_data)} observations to CSV: {output_path}")
    return os.path.abspath(output_path)


def _to_python_type(value: Any) -> Any:
    """Convert numpy types to Python native types for CSV/JSON."""
    if isinstance(value, (np.integer,)):
        return int(value)
    elif isinstance(value, (np.floating,)):
        return float(value)
    elif isinstance(value, np.ndarray):
        return value.tolist()
    elif isinstance(value, np.bool_):
        return bool(value)
    return value


def generate_trajectory_json(trajectory_data: List[Dict],
                              metadata: Optional[Dict] = None) -> Dict:
    """
    Generate JSON response for API endpoints.
    
    Args:
        trajectory_data: List of tracked cluster dictionaries
        metadata: Optional analysis metadata
        
    Returns:
        JSON-serializable dictionary
    """
    # Group by track_id
    tracks = {}
    for obs in trajectory_data:
        track_id = obs.get('track_id', 0)
        if track_id not in tracks:
            tracks[track_id] = {
                'track_id': track_id,
                'observations': [],
                'start_timestamp': None,
                'end_timestamp': None,
                'total_observations': 0
            }
        
        # Convert observation to JSON-safe format
        safe_obs = {k: _to_python_type(v) for k, v in obs.items()}
        tracks[track_id]['observations'].append(safe_obs)
        tracks[track_id]['total_observations'] += 1
        
        # Update timestamps
        ts = obs.get('timestamp')
        if ts:
            if tracks[track_id]['start_timestamp'] is None:
                tracks[track_id]['start_timestamp'] = ts
            tracks[track_id]['end_timestamp'] = ts
    
    # Calculate track statistics
    for track in tracks.values():
        observations = track['observations']
        if observations:
            track['mean_area_km2'] = float(np.mean([o.get('area_km2', 0) for o in observations]))
            track['mean_bt'] = float(np.mean([o.get('mean_bt', 0) for o in observations if o.get('mean_bt')]))
            track['min_bt_overall'] = float(min([o.get('min_bt', 999) for o in observations if o.get('min_bt')]))
    
    result = {
        'tracks': list(tracks.values()),
        'total_tracks': len(tracks),
        'total_observations': len(trajectory_data),
        'generated_at': datetime.utcnow().isoformat()
    }
    
    if metadata:
        result['metadata'] = {k: _to_python_type(v) for k, v in metadata.items()}
    
    return result


def create_visualization(bt_array: np.ndarray,
                          clusters: List[Dict],
                          output_path: str,
                          title: str = "TCC Detection") -> str:
    """
    Create visualization of detected clusters on BT image.
    
    Args:
        bt_array: Brightness temperature array
        clusters: List of detected cluster dictionaries
        output_path: Output image path (.png)
        title: Plot title
        
    Returns:
        Path to saved visualization
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Plot BT image
    im = ax.imshow(bt_array, cmap='jet_r', vmin=180, vmax=320)
    plt.colorbar(im, ax=ax, label='Brightness Temperature (K)', shrink=0.8)
    
    # Plot cluster centroids and radii
    for cluster in clusters:
        cx = cluster.get('centroid_x', cluster.get('centroid_pixel', (0, 0))[1])
        cy = cluster.get('centroid_y', cluster.get('centroid_pixel', (0, 0))[0])
        
        # Scale radius from km to pixels (approximate)
        radius_km = cluster.get('radius_km', 50)
        radius_pixels = radius_km / 4  # 4 km/pixel
        
        # Draw circle
        circle = Circle((cx, cy), radius_pixels, fill=False, 
                        edgecolor='white', linewidth=2)
        ax.add_patch(circle)
        
        # Add label
        track_id = cluster.get('track_id', cluster.get('cluster_id', '?'))
        ax.annotate(f"T{track_id}", (cx, cy - radius_pixels - 10),
                   color='white', fontsize=10, ha='center',
                   bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))
    
    ax.set_title(f"{title}\n{len(clusters)} clusters detected")
    ax.set_xlabel('Pixel X')
    ax.set_ylabel('Pixel Y')
    
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Created visualization: {output_path}")
    return output_path


def create_trajectory_plot(trajectory_data: List[Dict],
                            output_path: str,
                            title: str = "TCC Trajectories") -> str:
    """
    Create trajectory visualization showing cluster movement over time.
    
    Args:
        trajectory_data: List of tracked cluster observations
        output_path: Output image path (.png)
        title: Plot title
        
    Returns:
        Path to saved visualization
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Group by track_id
    tracks = {}
    for obs in trajectory_data:
        track_id = obs.get('track_id', 0)
        if track_id not in tracks:
            tracks[track_id] = {'lats': [], 'lons': [], 'times': []}
        
        tracks[track_id]['lats'].append(obs.get('centroid_lat', 0))
        tracks[track_id]['lons'].append(obs.get('centroid_lon', 0))
        tracks[track_id]['times'].append(obs.get('timestamp', ''))
    
    # Color map for different tracks
    colors = plt.cm.tab10(np.linspace(0, 1, len(tracks)))
    
    for (track_id, data), color in zip(tracks.items(), colors):
        lats = data['lats']
        lons = data['lons']
        
        # Plot trajectory line
        ax.plot(lons, lats, '-', color=color, linewidth=2, alpha=0.7,
               label=f'Track {track_id}')
        
        # Plot points
        ax.scatter(lons, lats, c=[color], s=30, zorder=5)
        
        # Mark start and end
        if len(lons) > 0:
            ax.scatter([lons[0]], [lats[0]], c=[color], s=100, marker='o',
                      edgecolors='black', linewidths=2, zorder=6)
            ax.scatter([lons[-1]], [lats[-1]], c=[color], s=100, marker='s',
                      edgecolors='black', linewidths=2, zorder=6)
    
    ax.set_xlabel('Longitude (°E)')
    ax.set_ylabel('Latitude (°N)')
    ax.set_title(f"{title}\n{len(tracks)} tracks, {len(trajectory_data)} observations")
    ax.legend(loc='upper left', fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # Set reasonable aspect ratio for geographic coordinates
    ax.set_aspect('equal')
    
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Created trajectory plot: {output_path}")
    return output_path
