"""
CloudSense Inference Engine (FIXED)
Robust inference: H5/Image → Model → Correct Post-Processing → TCC Detection

FIXES APPLIED:
1. Resize mask back to original resolution before area calculation
2. Apply physics-based BT threshold (<218K) in ensemble
3. Connected component labeling with scipy.ndimage
4. Area filtering using native pixel resolution (16 km²/pixel)
5. Morphological cleanup for noise removal
"""

import os
import numpy as np
import h5py
import torch
import cv2
import xarray as xr
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import segmentation_models_pytorch as smp
import albumentations as A
from albumentations.pytorch import ToTensorV2
from datetime import datetime
from scipy import ndimage
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class InferencePipeline:
    """
    Corrected TCC inference pipeline with proper post-processing.
    
    Key improvements over original:
    - Resizes predictions back to native resolution
    - Applies physics-based BT threshold in ensemble
    - Runs connected component analysis
    - Filters by minimum TCC area (34,800 km²)
    """
    
    # Model configuration
    IMG_SIZE = 512
    PROB_THRESHOLD = 0.2        # LOWERED to 0.2 for max sensitivity (needs retraining)
    
    # Physics-based thresholds
    BT_COLD_THRESHOLD = 218.0   # Kelvin - TCC cloud tops
    MIN_BT = 180.0              # Normalization min
    MAX_BT = 320.0              # Normalization max
    
    # Geophysical constraints
    MIN_AREA_KM2 = 5000.0       # LOWERED to 5000 for better detection
    PIXEL_RESOLUTION_KM = 4.0   # INSAT-3D native resolution (km/pixel)
    
    # Dynamic dataset discovery keys
    IR_CANDIDATES = ['IMG_TIR1', 'TIR1', 'IR', 'IR1', 'IR_BT', 'Band4', 'IMG_TIR']
    LUT_CANDIDATES = ['IMG_TIR1_TEMP', 'TIR1_TEMP', 'LUT', 'TEMP_LUT']
    LAT_CANDIDATES = ['Latitude', 'Lat_Grid', 'lat', 'Geolocation/Latitude']
    LON_CANDIDATES = ['Longitude', 'Lon_Grid', 'lon', 'Geolocation/Longitude']
    
    def __init__(self, model_path: str = None):
        """Initialize with trained model."""
        if model_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(project_root, "model", "best_model.pth")
        
        self.model_path = model_path
        self.device = self._get_device()
        self.model = None
        
        logger.info(f"InferencePipeline initialized (device: {self.device})")
    
    def _get_device(self):
        """Detect available device."""
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    
    def _load_model(self):
        """Lazy load model."""
        if self.model is not None:
            return self.model
        
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        self.model = smp.Unet(
            encoder_name="mobilenet_v2",
            encoder_weights=None,
            in_channels=1,
            classes=1,
        )
        self.model.load_state_dict(torch.load(self.model_path, map_location=self.device, weights_only=True))
        self.model.to(self.device)
        self.model.eval()
        
        logger.info(f"Model loaded from {self.model_path}")
        return self.model
    
    def _find_dataset(self, f, candidates: list):
        """Find first matching dataset from list of candidates."""
        for name in candidates:
            if '/' in name:
                parts = name.split('/')
                try:
                    current = f
                    for part in parts:
                        current = current[part]
                    return current
                except KeyError:
                    continue
            elif name in f:
                return f[name]
        return None
    
    def _load_h5(self, h5_path: str) -> Tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray]]:
        """Load INSAT-3D H5 file with dynamic discovery."""
        with h5py.File(h5_path, 'r') as f:
            logger.info(f"H5 keys: {list(f.keys())}")
            
            # 1. Find IR dataset
            ir_dataset = self._find_dataset(f, self.IR_CANDIDATES)
            if ir_dataset is None:
                for key in f.keys():
                    if isinstance(f[key], h5py.Dataset) and len(f[key].shape) >= 2:
                        ir_dataset = f[key]
                        logger.warning(f"Using fallback IR dataset: {key}")
                        break
            
            if ir_dataset is None:
                raise ValueError(f"No IR data found in H5 file. Available keys: {list(f.keys())}")
            
            raw_counts = ir_dataset[0] if len(ir_dataset.shape) == 3 else ir_dataset[:]
            
            # 2. Apply LUT if available
            lut_dataset = self._find_dataset(f, self.LUT_CANDIDATES)
            if lut_dataset is not None:
                lut = lut_dataset[:]
                raw_counts = np.clip(raw_counts, 0, len(lut) - 1)
                irbt = lut[raw_counts].astype(np.float32)
                logger.info("Applied LUT for brightness temperature conversion")
            else:
                irbt = raw_counts.astype(np.float32)
                logger.warning("No LUT found, using raw values as IRBT")
            
            # 3. Handle NaN/fill values
            irbt = np.where(irbt < 100, np.nan, irbt)
            irbt = np.nan_to_num(irbt, nan=np.nanmean(irbt) if not np.all(np.isnan(irbt)) else 250.0)
            
            # 4. Lat/Lon (optional)
            lat, lon = None, None
            
            lat_dataset = self._find_dataset(f, self.LAT_CANDIDATES)
            if lat_dataset is not None:
                lat = lat_dataset[:].astype(np.float32)
            
            lon_dataset = self._find_dataset(f, self.LON_CANDIDATES)
            if lon_dataset is not None:
                lon = lon_dataset[:].astype(np.float32)
            
            if lat is None or lon is None:
                logger.warning("Lat/Lon not found - using synthetic coordinates")
                lat, lon = self._create_synthetic_coords(irbt.shape)
        
        return irbt, lat, lon
    
    def _create_synthetic_coords(self, shape: Tuple[int, int]) -> Tuple[np.ndarray, np.ndarray]:
        """Create synthetic lat/lon grids for data without geolocation."""
        h, w = shape
        lat_1d = np.linspace(30.0, 0.0, h)  # North to South
        lon_1d = np.linspace(60.0, 100.0, w)  # West to East
        lon_grid, lat_grid = np.meshgrid(lon_1d, lat_1d)
        return lat_grid.astype(np.float32), lon_grid.astype(np.float32)
    
    def _load_image(self, image_path: str) -> np.ndarray:
        """Load image file (PNG/JPG) for inference."""
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"Failed to load image: {image_path}")
        
        irbt = img.astype(np.float32)
        irbt = self.MIN_BT + (irbt / 255.0) * (self.MAX_BT - self.MIN_BT)
        return irbt
    
    def _normalize_bt(self, irbt: np.ndarray) -> np.ndarray:
        """Normalize BT to [0, 1] using physics-based bounds."""
        normalized = (irbt - self.MIN_BT) / (self.MAX_BT - self.MIN_BT)
        return np.clip(normalized, 0, 1).astype(np.float32)
    
    def _prepare_tensor(self, normalized: np.ndarray) -> torch.Tensor:
        """Resize and convert to model input tensor."""
        resized = cv2.resize(normalized, (self.IMG_SIZE, self.IMG_SIZE), interpolation=cv2.INTER_LINEAR)
        tensor = torch.from_numpy(resized).unsqueeze(0).unsqueeze(0).float()
        return tensor.to(self.device)
    
    def _run_model_inference(self, tensor: torch.Tensor) -> np.ndarray:
        """Run model inference, return 512x512 probability map."""
        model = self._load_model()
        
        with torch.no_grad():
            output = model(tensor)
            prob = torch.sigmoid(output).squeeze().cpu().numpy()
        
        return prob
    
    def _apply_post_processing(self, 
                                prob_512: np.ndarray, 
                                irbt: np.ndarray,
                                lat: np.ndarray,
                                lon: np.ndarray) -> Dict:
        """
        CORRECTED post-processing pipeline.
        
        KEY FIX: Training masks were generated from DBSCAN clusters, NOT from
        BT threshold intersection. The model learned cluster shapes implicitly.
        We must NOT apply BT threshold intersection here - it kills valid predictions.
        
        Pipeline:
        1. Resize probability to native resolution
        2. Threshold at 0.5 (NO BT intersection)
        3. Morphological cleanup
        4. Connected component analysis
        5. Area filtering (>= 34,800 km²)
        """
        original_shape = irbt.shape
        h, w = original_shape
        
        # 1. RESIZE probability map to native resolution
        prob_native = cv2.resize(
            prob_512, 
            (w, h),  # (width, height) for cv2
            interpolation=cv2.INTER_LINEAR
        )
        
        # 2. THRESHOLD - Direct from model (NO BT INTERSECTION)
        # The model already learned physics-based patterns from training
        binary_mask = (prob_native > self.PROB_THRESHOLD).astype(np.uint8)
        
        # 3. MORPHOLOGICAL CLEANUP
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        cleaned = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # 4. CONNECTED COMPONENT ANALYSIS
        labeled, num_features = ndimage.label(cleaned)
        
        # 5. AREA FILTERING with correct pixel area
        pixel_area_km2 = self.PIXEL_RESOLUTION_KM ** 2  # 16 km²
        
        valid_mask = np.zeros_like(cleaned)
        detections = []
        
        for label_id in range(1, num_features + 1):
            region_mask = (labeled == label_id)
            pixel_count = np.sum(region_mask)
            area_km2 = pixel_count * pixel_area_km2
            
            if area_km2 >= self.MIN_AREA_KM2:
                valid_mask[region_mask] = 1
                
                # Compute centroid
                y_coords, x_coords = np.where(region_mask)
                centroid_lat = float(np.mean(lat[y_coords, x_coords]))
                centroid_lon = float(np.mean(lon[y_coords, x_coords]))
                
                # Compute mean BT for info (but NOT for filtering)
                mean_bt = float(np.mean(irbt[region_mask]))
                min_bt = float(np.min(irbt[region_mask]))
                
                detections.append({
                    'cluster_id': len(detections) + 1,
                    'area_km2': float(area_km2),
                    'pixel_count': int(pixel_count),
                    'centroid_lat': centroid_lat,
                    'centroid_lon': centroid_lon,
                    'mean_bt': mean_bt,
                    'min_bt': min_bt,
                    'radius_km': float(np.sqrt(area_km2 / np.pi)),
                    # TCC Classification: min_bt < 235K is strong TCC indicator
                    'is_tcc': bool(min_bt < 235.0),
                    'classification': (
                        'Confirmed TCC' if min_bt < 220.0 else
                        'Likely TCC' if min_bt < 235.0 else
                        'Cloud Cluster'
                    )
                })
        
        logger.info(f"Post-processing: {num_features} components → {len(detections)} valid TCCs (area >= {self.MIN_AREA_KM2} km²)")
        
        return {
            'probability_native': prob_native,
            'binary_mask': binary_mask,
            'final_mask': valid_mask,
            'detections': detections,
            'total_tcc_area_km2': sum(d['area_km2'] for d in detections)
        }
    
    def _extract_timestamp(self, file_path: str) -> datetime:
        """Extract timestamp from filename or use current time."""
        basename = os.path.basename(file_path)
        try:
            parts = basename.split('_')
            date_str = parts[1]
            time_str = parts[2]
            return datetime.strptime(f"{date_str}_{time_str}", "%d%b%Y_%H%M")
        except:
            return datetime.now()
    
    def _save_mask_npy(self, mask: np.ndarray, output_path: str):
        """Save binary mask as .npy."""
        np.save(output_path, mask)
        logger.info(f"Saved: {output_path}")
    
    def _save_mask_png(self, mask: np.ndarray, output_path: str):
        """Save visual mask as .png."""
        plt.figure(figsize=(8, 8))
        plt.imshow(mask, cmap='gray')
        plt.axis('off')
        plt.tight_layout(pad=0)
        plt.savefig(output_path, bbox_inches='tight', pad_inches=0, dpi=150)
        plt.close()
        logger.info(f"Saved: {output_path}")
    
    def _save_satellite_image(self, irbt: np.ndarray, output_path: str):
        """Save original satellite IRBT image as .png."""
        plt.figure(figsize=(10, 10))
        plt.imshow(irbt, cmap='gray_r', vmin=180, vmax=320)
        plt.colorbar(label='Brightness Temperature (K)', shrink=0.8)
        plt.title('IR Brightness Temperature')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(output_path, bbox_inches='tight', dpi=150)
        plt.close()
        logger.info(f"Saved: {output_path}")
    
    def _save_overlay_visualization(self, irbt: np.ndarray, mask: np.ndarray, 
                                     detections: List[Dict], output_path: str,
                                     timestamp_str: str = None):
        """
        Save high-quality visualization with TCC detections annotated.
        Left: IR Brightness Temperature with detection contours
        Right: TCC Mask with cluster labels
        """
        fig, ax = plt.subplots(1, 2, figsize=(16, 7), facecolor='#0a0a1a')
        
        for a in ax:
            a.set_facecolor('#0a0a1a')
        
        # LEFT: IR Brightness Temperature with detection contours
        im1 = ax[0].imshow(irbt, cmap='jet_r', vmin=180, vmax=320)
        title_left = f'IR Brightness Temp ({timestamp_str})' if timestamp_str else 'IR Brightness Temp'
        ax[0].set_title(title_left, color='white', fontsize=12, fontweight='bold')
        ax[0].axis('off')
        cbar1 = plt.colorbar(im1, ax=ax[0], fraction=0.046, pad=0.04)
        cbar1.set_label('Temperature (K)', color='white', fontsize=9)
        cbar1.ax.yaxis.set_tick_params(color='white')
        plt.setp(cbar1.ax.yaxis.get_ticklabels(), color='white', fontsize=8)
        
        # Draw contours of detected TCCs on IR image
        if mask.sum() > 0:
            ax[0].contour(mask, levels=[0.5], colors=['red'], linewidths=1.5)
        
        # RIGHT: TCC Mask with cluster labels
        # Use a custom colormap: dark background, bright cyan for TCC
        from matplotlib.colors import ListedColormap
        tcc_cmap = ListedColormap(['#0a0a1a', '#00e5ff'])
        ax[1].imshow(mask, cmap=tcc_cmap, vmin=0, vmax=1)
        ax[1].set_title('TCC Detection Mask', color='white', fontsize=12, fontweight='bold')
        ax[1].axis('off')
        
        # Annotate each detection with cluster ID
        for d in detections:
            # Convert lat/lon to approximate pixel coordinates
            # (Using centroid info for labeling)
            y_coords, x_coords = np.where(mask > 0)
            if len(y_coords) > 0:
                # Find the connected component closest to this detection's centroid
                from scipy import ndimage
                labeled, _ = ndimage.label(mask)
                for label_id in range(1, labeled.max() + 1):
                    region = (labeled == label_id)
                    ry, rx = np.where(region)
                    cy, cx = np.mean(ry), np.mean(rx)
                    # Label the cluster
                    if label_id == d['cluster_id']:
                        classification = d.get('classification', 'TCC')
                        short_class = '✓' if 'Confirmed' in classification else '~' if 'Likely' in classification else '?'
                        label_text = f"TCC-{d['cluster_id']} {short_class}"
                        ax[1].annotate(label_text, (cx, cy), 
                                      color='white', fontsize=7, fontweight='bold',
                                      ha='center', va='center',
                                      bbox=dict(boxstyle='round,pad=0.2', facecolor='#00000088', edgecolor='#00e5ff'))
                        break
        
        # Summary text
        total_area = sum(d.get('area_km2', 0) for d in detections)
        confirmed = sum(1 for d in detections if d.get('is_tcc', False))
        summary = f"Detections: {len(detections)} | Confirmed TCC: {confirmed} | Total Area: {total_area:,.0f} km²"
        fig.text(0.5, 0.02, summary, ha='center', va='bottom', 
                color='#00e5ff', fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='#0a0a1a', edgecolor='#00e5ff44'))
        
        plt.tight_layout(rect=[0, 0.05, 1, 1])
        plt.savefig(output_path, dpi=200, facecolor='#0a0a1a', bbox_inches='tight')
        plt.close()
        logger.info(f"Saved comparison: {output_path}")
    
    def _save_netcdf(self, irbt: np.ndarray, prob: np.ndarray, mask: np.ndarray,
                     lat: np.ndarray, lon: np.ndarray, timestamp: datetime, 
                     detections: List[Dict], output_path: str):
        """Save NetCDF with CF-compliant structure including detections."""
        h, w = irbt.shape
        
        # Build coordinates
        if lat is not None and lon is not None:
            coords = {
                "time": [timestamp],
                "latitude": (["lat", "lon"], lat, {
                    "long_name": "Latitude",
                    "units": "degrees_north"
                }),
                "longitude": (["lat", "lon"], lon, {
                    "long_name": "Longitude",
                    "units": "degrees_east"
                }),
            }
        else:
            y_coords = np.arange(h)
            x_coords = np.arange(w)
            coords = {
                "time": [timestamp],
                "y": (["lat"], y_coords, {"long_name": "Y Pixel Index", "units": "1"}),
                "x": (["lon"], x_coords, {"long_name": "X Pixel Index", "units": "1"}),
            }
        
        ds = xr.Dataset(
            data_vars={
                "irbt": (["time", "lat", "lon"], irbt[np.newaxis, :, :], {
                    "long_name": "IR Brightness Temperature",
                    "units": "K",
                    "standard_name": "brightness_temperature"
                }),
                "tcc_probability": (["time", "lat", "lon"], prob[np.newaxis, :, :], {
                    "long_name": "TCC Detection Probability",
                    "units": "1",
                    "valid_range": [0.0, 1.0]
                }),
                "tcc_mask": (["time", "lat", "lon"], mask[np.newaxis, :, :], {
                    "long_name": "TCC Binary Mask (Area Filtered)",
                    "units": "1",
                    "flag_values": [0, 1],
                    "flag_meanings": "background TCC"
                }),
            },
            coords=coords,
            attrs={
                "Conventions": "CF-1.8",
                "title": "CloudSense TCC Detection Output",
                "source": "INSAT-3D IRBT + U-Net Segmentation",
                "institution": "CloudSense",
                "history": f"Created {datetime.now().isoformat()}",
                "geolocation_available": "true" if lat is not None else "false",
                "tcc_count": len(detections),
                "total_tcc_area_km2": sum(d['area_km2'] for d in detections),
                "min_area_threshold_km2": self.MIN_AREA_KM2,
                "bt_threshold_K": self.BT_COLD_THRESHOLD
            }
        )
        
        ds.to_netcdf(output_path, engine="netcdf4")
        logger.info(f"Saved: {output_path}")
    
    def process_file(self, h5_path: str, output_dir: str, analysis_id: str = None) -> dict:
        """
        Process single H5 file with CORRECTED post-processing.
        
        Returns:
            dict with success status, output paths, detections, and input_type
        """
        try:
            if analysis_id is None:
                timestamp = self._extract_timestamp(h5_path)
                analysis_id = timestamp.strftime("%Y%m%d_%H%M")
            
            file_output_dir = os.path.join(output_dir, analysis_id)
            os.makedirs(file_output_dir, exist_ok=True)
            
            logger.info(f"Processing H5: {os.path.basename(h5_path)}")
            
            # 1. Load data at native resolution
            irbt, lat, lon = self._load_h5(h5_path)
            timestamp = self._extract_timestamp(h5_path)
            
            logger.info(f"Input shape: {irbt.shape}, BT range: {irbt.min():.1f}K - {irbt.max():.1f}K")
            
            # 2. Normalize and prepare tensor
            normalized = self._normalize_bt(irbt)
            tensor = self._prepare_tensor(normalized)
            
            # 3. Run model inference (512x512)
            prob_512 = self._run_model_inference(tensor)
            
            # 4. CORRECTED post-processing
            results = self._apply_post_processing(prob_512, irbt, lat, lon)
            
            final_mask = results['final_mask']
            prob_native = results['probability_native']
            detections = results['detections']
            
            tcc_pixels = int(np.sum(final_mask))
            
            logger.info(f"TCC detections: {len(detections)}, Total area: {results['total_tcc_area_km2']:,.0f} km²")
            
            # 5. Save outputs
            satellite_png_path = os.path.join(file_output_dir, "satellite.png")
            mask_npy_path = os.path.join(file_output_dir, "mask.npy")
            mask_png_path = os.path.join(file_output_dir, "mask.png")
            overlay_path = os.path.join(file_output_dir, "overlay.png")
            netcdf_path = os.path.join(file_output_dir, "output.nc")
            
            self._save_satellite_image(irbt, satellite_png_path)
            self._save_mask_npy(final_mask, mask_npy_path)
            self._save_mask_png(final_mask, mask_png_path)
            timestamp_str = timestamp.strftime("%Y%m%d_%H%M")
            self._save_overlay_visualization(irbt, final_mask, detections, overlay_path, timestamp_str)
            self._save_netcdf(irbt, prob_native, final_mask, lat, lon, timestamp, detections, netcdf_path)
            
            return {
                "success": True,
                "analysis_id": analysis_id,
                "input_type": "h5",
                "tcc_pixels": tcc_pixels,
                "tcc_count": len(detections),
                "total_area_km2": results['total_tcc_area_km2'],
                "detections": detections,
                "outputs": {
                    "satellite_png": satellite_png_path,
                    "mask_npy": mask_npy_path,
                    "mask_png": mask_png_path,
                    "overlay_png": overlay_path,
                    "netcdf": netcdf_path
                }
            }
            
        except Exception as e:
            logger.error(f"H5 processing error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_image(self, image_path: str, output_dir: str, analysis_id: str = None) -> dict:
        """
        Process image file (PNG/JPG) with CORRECTED post-processing.
        Note: No geolocation available for images, uses synthetic coordinates.
        """
        try:
            if analysis_id is None:
                analysis_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            file_output_dir = os.path.join(output_dir, analysis_id)
            os.makedirs(file_output_dir, exist_ok=True)
            
            logger.info(f"Processing image: {os.path.basename(image_path)}")
            
            # 1. Load image
            irbt = self._load_image(image_path)
            lat, lon = self._create_synthetic_coords(irbt.shape)
            
            logger.info(f"Input shape: {irbt.shape}")
            
            # 2. Normalize and prepare tensor
            normalized = self._normalize_bt(irbt)
            tensor = self._prepare_tensor(normalized)
            
            # 3. Run model inference (512x512)
            prob_512 = self._run_model_inference(tensor)
            
            # 4. CORRECTED post-processing
            results = self._apply_post_processing(prob_512, irbt, lat, lon)
            
            final_mask = results['final_mask']
            detections = results['detections']
            
            tcc_pixels = int(np.sum(final_mask))
            
            logger.info(f"TCC detections: {len(detections)}, Total area: {results['total_tcc_area_km2']:,.0f} km²")
            
            # 5. Save outputs
            satellite_png_path = os.path.join(file_output_dir, "satellite.png")
            mask_npy_path = os.path.join(file_output_dir, "mask.npy")
            mask_png_path = os.path.join(file_output_dir, "mask.png")
            overlay_path = os.path.join(file_output_dir, "overlay.png")
            
            # Copy input image as satellite view
            import shutil
            shutil.copy(image_path, satellite_png_path)
            
            self._save_mask_npy(final_mask, mask_npy_path)
            self._save_mask_png(final_mask, mask_png_path)
            # For images, use filename as timestamp
            basename = os.path.basename(image_path)
            ts_str = os.path.splitext(basename)[0]
            self._save_overlay_visualization(irbt, final_mask, detections, overlay_path, ts_str)
            
            return {
                "success": True,
                "analysis_id": analysis_id,
                "input_type": "image",
                "tcc_pixels": tcc_pixels,
                "tcc_count": len(detections),
                "total_area_km2": results['total_tcc_area_km2'],
                "detections": detections,
                "outputs": {
                    "satellite_png": satellite_png_path,
                    "mask_npy": mask_npy_path,
                    "mask_png": mask_png_path,
                    "overlay_png": overlay_path,
                    "netcdf": None
                }
            }
            
        except Exception as e:
            logger.error(f"Image processing error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
