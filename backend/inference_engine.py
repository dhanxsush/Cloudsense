"""
CloudSense Inference Engine
Minimal inference: H5 → Model → 3 Outputs (mask.npy, mask.png, output.nc)
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
import logging

logger = logging.getLogger(__name__)


class InferencePipeline:
    """Minimal TCC inference pipeline"""
    
    # Configuration
    IMG_SIZE = 512
    THRESHOLD = 0.5
    MIN_BT = 180.0
    MAX_BT = 320.0
    
    def __init__(self, model_path: str = None):
        """Initialize with trained model"""
        if model_path is None:
            # Default: look in training/models/
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(project_root, "training", "models", "best_model.pth")
        
        self.model_path = model_path
        self.device = self._get_device()
        self.model = None
        
        logger.info(f"InferencePipeline initialized (device: {self.device})")
    
    def _get_device(self):
        """Detect available device"""
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    
    def _load_model(self):
        """Lazy load model"""
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
    
    def _load_h5(self, h5_path: str):
        """Load INSAT-3D H5 file"""
        with h5py.File(h5_path, 'r') as f:
            raw_counts = f['IMG_TIR1'][0]
            lut = f['IMG_TIR1_TEMP'][:]
            irbt = lut[raw_counts].astype(np.float32)
            lat = f['Latitude'][:].astype(np.float32)
            lon = f['Longitude'][:].astype(np.float32)
        return irbt, lat, lon
    
    def _preprocess(self, irbt: np.ndarray):
        """Normalize and transform for model input"""
        normalized = (irbt - self.MIN_BT) / (self.MAX_BT - self.MIN_BT)
        normalized = np.clip(normalized, 0, 1).astype(np.float32)
        
        transform = A.Compose([
            A.Resize(self.IMG_SIZE, self.IMG_SIZE),
            ToTensorV2()
        ])
        
        tensor = transform(image=normalized)['image']
        return tensor.unsqueeze(0)
    
    def _run_inference(self, tensor):
        """Run model inference"""
        model = self._load_model()
        tensor = tensor.to(self.device)
        
        with torch.no_grad():
            output = model(tensor)
            prob = torch.sigmoid(output).squeeze().cpu().numpy()
        
        mask = (prob > self.THRESHOLD).astype(np.uint8)
        return prob, mask
    
    def _extract_timestamp(self, h5_path: str) -> datetime:
        """Extract timestamp from H5 filename"""
        basename = os.path.basename(h5_path)
        try:
            parts = basename.split('_')
            date_str = parts[1]
            time_str = parts[2]
            return datetime.strptime(f"{date_str}_{time_str}", "%d%b%Y_%H%M")
        except:
            return datetime.now()
    
    def _save_mask_npy(self, mask: np.ndarray, output_path: str):
        """Save binary mask as .npy"""
        np.save(output_path, mask)
        logger.info(f"Saved: {output_path}")
    
    def _save_mask_png(self, mask: np.ndarray, output_path: str):
        """Save visual mask as .png"""
        plt.figure(figsize=(8, 8))
        plt.imshow(mask, cmap='gray')
        plt.axis('off')
        plt.tight_layout(pad=0)
        plt.savefig(output_path, bbox_inches='tight', pad_inches=0, dpi=150)
        plt.close()
        logger.info(f"Saved: {output_path}")
    
    def _save_netcdf(self, irbt: np.ndarray, prob: np.ndarray, mask: np.ndarray,
                     lat: np.ndarray, lon: np.ndarray, timestamp: datetime, output_path: str):
        """Save NetCDF with CF-compliant structure"""
        h, w = irbt.shape
        prob_resized = cv2.resize(prob, (w, h), interpolation=cv2.INTER_LINEAR)
        mask_resized = cv2.resize(mask.astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST).astype(np.uint8)
        
        ds = xr.Dataset(
            data_vars={
                "irbt": (["time", "lat", "lon"], irbt[np.newaxis, :, :], {
                    "long_name": "IR Brightness Temperature",
                    "units": "K",
                    "standard_name": "brightness_temperature"
                }),
                "tcc_probability": (["time", "lat", "lon"], prob_resized[np.newaxis, :, :], {
                    "long_name": "TCC Detection Probability",
                    "units": "1",
                    "valid_range": [0.0, 1.0]
                }),
                "tcc_mask": (["time", "lat", "lon"], mask_resized[np.newaxis, :, :], {
                    "long_name": "TCC Binary Mask",
                    "units": "1",
                    "flag_values": [0, 1],
                    "flag_meanings": "background TCC"
                }),
            },
            coords={
                "time": [timestamp],
                "latitude": (["lat", "lon"], lat, {
                    "long_name": "Latitude",
                    "units": "degrees_north"
                }),
                "longitude": (["lat", "lon"], lon, {
                    "long_name": "Longitude",
                    "units": "degrees_east"
                }),
            },
            attrs={
                "Conventions": "CF-1.8",
                "title": "CloudSense TCC Detection Output",
                "source": "INSAT-3D IRBT + U-Net Segmentation",
                "institution": "CloudSense",
                "history": f"Created {datetime.now().isoformat()}",
            }
        )
        
        ds.to_netcdf(output_path, engine="netcdf4")
        logger.info(f"Saved: {output_path}")
    
    def process_file(self, h5_path: str, output_dir: str, analysis_id: str = None) -> dict:
        """
        Process single H5 file and generate 3 outputs.
        
        Returns:
            dict with success status and output paths
        """
        try:
            # Use analysis_id or timestamp for output folder
            if analysis_id is None:
                timestamp = self._extract_timestamp(h5_path)
                analysis_id = timestamp.strftime("%Y%m%d_%H%M")
            
            # Create output directory
            file_output_dir = os.path.join(output_dir, analysis_id)
            os.makedirs(file_output_dir, exist_ok=True)
            
            logger.info(f"Processing: {os.path.basename(h5_path)}")
            
            # Load data
            irbt, lat, lon = self._load_h5(h5_path)
            timestamp = self._extract_timestamp(h5_path)
            
            # Preprocess
            tensor = self._preprocess(irbt)
            
            # Inference
            prob, mask = self._run_inference(tensor)
            tcc_pixels = int(np.sum(mask))
            
            logger.info(f"TCC pixels detected: {tcc_pixels}")
            
            # Save outputs
            mask_npy_path = os.path.join(file_output_dir, "mask.npy")
            mask_png_path = os.path.join(file_output_dir, "mask.png")
            netcdf_path = os.path.join(file_output_dir, "output.nc")
            
            self._save_mask_npy(mask, mask_npy_path)
            self._save_mask_png(mask, mask_png_path)
            self._save_netcdf(irbt, prob, mask, lat, lon, timestamp, netcdf_path)
            
            return {
                "success": True,
                "analysis_id": analysis_id,
                "tcc_pixels": tcc_pixels,
                "outputs": {
                    "mask_npy": mask_npy_path,
                    "mask_png": mask_png_path,
                    "netcdf": netcdf_path
                }
            }
            
        except Exception as e:
            logger.error(f"Processing error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
