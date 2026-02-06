"""
TCC Detection Pipeline
Orchestrates all 8 modules for complete TCC detection and tracking.
"""

import os
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import numpy as np

from .preprocessing import (
    load_h5_file, 
    normalize_bt, 
    extract_timestamp_string,
    get_pixel_area_km2
)
from .thresholding import apply_bt_threshold
from .clustering import (
    cluster_clouds, 
    apply_geophysical_constraints,
    get_cluster_as_dict
)
from .segmentation import load_unet_model, segment, ensemble_with_threshold
from .feature_extraction import compute_cluster_features
from .tracking import TCCTracker
from .output import export_to_netcdf, export_to_csv, generate_trajectory_json

logger = logging.getLogger(__name__)

# Default paths - model is in project root /cloudsense/training/models/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # /cloudsense
DEFAULT_MODEL_PATH = os.path.join(PROJECT_ROOT, "training", "models", "best_model.pth")



class TCCPipeline:
    """
    Complete TCC Detection and Tracking Pipeline.
    
    Orchestrates all 8 modules:
    1. Preprocessing - H5 loading, normalization
    2. Thresholding - Physical BT constraint
    3. Clustering - DBSCAN with geophysical validation
    4. Pseudo-labels - Training mask generation
    5. Segmentation - U-Net inference
    6. Feature extraction - Cluster metrics
    7. Tracking - Kalman filter trajectory
    8. Output - NetCDF/CSV/JSON export
    """
    
    def __init__(self, 
                 model_path: Optional[str] = None,
                 bt_threshold: float = 218.0,
                 min_area_km2: float = 34800.0,
                 use_gpu: bool = False):
        """
        Initialize pipeline.
        
        Args:
            model_path: Path to trained U-Net model
            bt_threshold: BT threshold for cold cloud detection (K)
            min_area_km2: Minimum TCC area (km²)
            use_gpu: Whether to use GPU for DBSCAN clustering
        """
        self.bt_threshold = bt_threshold
        self.min_area_km2 = min_area_km2
        self.use_gpu = use_gpu
        
        # Resolve model path
        if model_path is None:
            if os.path.exists(DEFAULT_MODEL_PATH):
                model_path = DEFAULT_MODEL_PATH
            else:
                raise FileNotFoundError(
                    f"Model not found at {DEFAULT_MODEL_PATH}"
                )
        
        self.model_path = model_path
        self.model = load_unet_model(model_path)
        self.tracker = TCCTracker()
        
        # Results storage
        self.all_results: List[Dict] = []
        
        logger.info(f"TCCPipeline initialized with model: {model_path}")
    
    def process_frame(self, h5_path: str) -> List[Dict]:
        """
        Process a single H5 file through the complete pipeline.
        
        Args:
            h5_path: Path to INSAT-3D H5 file
            
        Returns:
            List of tracked cluster dictionaries with full features
        """
        timestamp = extract_timestamp_string(h5_path)
        
        try:
            # Module 1: Preprocessing
            bt_array, lat_grid, lon_grid = load_h5_file(h5_path)
            logger.debug(f"Loaded {h5_path}, shape: {bt_array.shape}")
            
            # Module 2: Physical thresholding
            bt_mask = apply_bt_threshold(bt_array, self.bt_threshold)
            
            # Module 5: U-Net segmentation
            unet_mask = segment(self.model, bt_array)
            
            # Ensemble: combine U-Net with BT threshold
            refined_mask = ensemble_with_threshold(unet_mask, bt_mask, mode='intersection')
            
            # Module 3: Clustering
            clusters = cluster_clouds(
                refined_mask, lat_grid, lon_grid, 
                use_gpu=self.use_gpu
            )
            
            # Apply geophysical constraints
            valid_clusters = apply_geophysical_constraints(
                clusters, 
                min_area_km2=self.min_area_km2
            )
            
            # Module 6: Feature extraction
            cluster_dicts = []
            for cluster in valid_clusters:
                features = compute_cluster_features(
                    cluster.pixel_coords,
                    bt_array,
                    lat_grid,
                    lon_grid,
                    cluster.cluster_id
                )
                cluster_dicts.append(features)
            
            # Module 7: Tracking
            tracked = self.tracker.update(cluster_dicts, timestamp)
            
            # Store results
            self.all_results.extend(tracked)
            
            logger.info(f"Processed {timestamp}: {len(tracked)} clusters tracked")
            return tracked
            
        except Exception as e:
            logger.error(f"Error processing {h5_path}: {e}")
            return []
    
    def process_directory(self, 
                          input_dir: str,
                          output_dir: Optional[str] = None,
                          recursive: bool = True) -> Dict:
        """
        Process all H5 files in a directory.
        
        Args:
            input_dir: Directory containing H5 files
            output_dir: Optional output directory for exports
            recursive: Whether to search subdirectories
            
        Returns:
            Summary dictionary with processing results
        """
        # Collect H5 files
        h5_files = []
        if recursive:
            for root, dirs, files in os.walk(input_dir):
                for f in files:
                    if f.endswith('.h5'):
                        h5_files.append(os.path.join(root, f))
        else:
            for f in os.listdir(input_dir):
                if f.endswith('.h5'):
                    h5_files.append(os.path.join(input_dir, f))
        
        # Sort chronologically by filename
        h5_files.sort()
        
        logger.info(f"Processing {len(h5_files)} H5 files from {input_dir}")
        
        # Reset tracker and results
        self.tracker.reset()
        self.all_results.clear()
        
        # Process each file
        processed = 0
        errors = 0
        
        for h5_path in h5_files:
            try:
                self.process_frame(h5_path)
                processed += 1
            except Exception as e:
                logger.error(f"Failed to process {h5_path}: {e}")
                errors += 1
        
        # Export results if output directory specified
        export_paths = {}
        if output_dir and self.all_results:
            os.makedirs(output_dir, exist_ok=True)
            
            # CSV export
            csv_path = os.path.join(output_dir, "trajectory.csv")
            export_to_csv(self.all_results, csv_path)
            export_paths['csv'] = csv_path
            
            # NetCDF export
            nc_path = os.path.join(output_dir, "trajectory.nc")
            metadata = {
                'source_directory': input_dir,
                'files_processed': processed,
                'bt_threshold': self.bt_threshold,
                'min_area_km2': self.min_area_km2
            }
            export_to_netcdf(self.all_results, metadata, nc_path)
            export_paths['netcdf'] = nc_path
        
        summary = {
            'files_processed': processed,
            'files_failed': errors,
            'total_observations': len(self.all_results),
            'active_tracks': len(self.tracker.tracks),
            'exports': export_paths
        }
        
        logger.info(f"Pipeline complete: {summary}")
        return summary
    
    def get_results(self) -> List[Dict]:
        """Get all accumulated results."""
        return self.all_results.copy()
    
    def get_trajectory_json(self) -> Dict:
        """Get results as JSON-formatted dictionary."""
        metadata = {
            'model_path': self.model_path,
            'bt_threshold': self.bt_threshold,
            'min_area_km2': self.min_area_km2
        }
        return generate_trajectory_json(self.all_results, metadata)
    
    def get_predictions(self, steps: int = 6) -> Dict:
        """
        Get future position predictions for all active tracks.
        
        Uses Kalman filter velocity estimates to predict where each 
        TCC will move in the next few hours.
        
        Args:
            steps: Number of future time steps (default 6 = 3 hours at 30min intervals)
            
        Returns:
            Dictionary with predictions for each track
        """
        predictions = self.tracker.get_all_predictions(steps=steps)
        
        return {
            'predictions': predictions,
            'active_tracks': len(predictions),
            'prediction_interval_hours': 0.5,
            'total_steps': steps,
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def generate_report(self, output_dir: str) -> Dict:
        """
        Generate comprehensive analysis report with all exports.
        
        Creates:
        - NetCDF file (CF-compliant for meteorology tools)
        - CSV file (trajectory data)
        - JSON summary
        - Predictions JSON
        
        Args:
            output_dir: Directory to save report files
            
        Returns:
            Dictionary with report paths and summary
        """
        import json
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Metadata
        metadata = {
            'model_path': self.model_path,
            'bt_threshold': self.bt_threshold,
            'min_area_km2': self.min_area_km2,
            'generated_at': datetime.utcnow().isoformat(),
            'total_observations': len(self.all_results),
            'active_tracks': len(self.tracker.tracks)
        }
        
        exports = {}
        
        # 1. NetCDF export
        nc_path = os.path.join(output_dir, "tcc_trajectory.nc")
        try:
            export_to_netcdf(self.all_results, metadata, nc_path)
            exports['netcdf'] = nc_path
            logger.info(f"NetCDF exported: {nc_path}")
        except ImportError:
            exports['netcdf'] = None
            logger.warning("netCDF4 not installed, skipping NetCDF export")
        
        # 2. CSV export
        csv_path = os.path.join(output_dir, "tcc_trajectory.csv")
        export_to_csv(self.all_results, csv_path)
        exports['csv'] = csv_path
        
        # 3. JSON trajectory
        json_path = os.path.join(output_dir, "tcc_analysis.json")
        trajectory_json = generate_trajectory_json(self.all_results, metadata)
        with open(json_path, 'w') as f:
            json.dump(trajectory_json, f, indent=2)
        exports['json'] = json_path
        
        # 4. Predictions JSON
        pred_path = os.path.join(output_dir, "tcc_predictions.json")
        predictions = self.get_predictions()
        with open(pred_path, 'w') as f:
            json.dump(predictions, f, indent=2)
        exports['predictions'] = pred_path
        
        report = {
            'status': 'complete',
            'metadata': metadata,
            'exports': exports,
            'summary': {
                'total_tracks': len(self.tracker.tracks),
                'total_observations': len(self.all_results),
                'prediction_steps': 6
            }
        }
        
        logger.info(f"Report generated: {exports}")
        return report
    
    def reset(self):
        """Reset pipeline state for new processing run."""
        self.tracker.reset()
        self.all_results.clear()


# Legacy compatibility alias
TCCAnalysisEngine = TCCPipeline
AnalysisEngine = TCCPipeline
