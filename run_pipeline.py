"""
CloudSense TCC Inference Pipeline
Minimal pipeline: MOSDAC Download → Inference → 3 Outputs Only

Outputs:
  - mask.npy    : Binary segmentation mask
  - mask.png    : Visual segmentation mask
  - output.nc   : NetCDF with IRBT, probability, and mask

Usage:
  1. Configure config.json for MOSDAC API
  2. Run: python run_pipeline.py
"""

import os
import glob
import numpy as np
import h5py
import torch
import cv2
import xarray as xr
import matplotlib.pyplot as plt
import segmentation_models_pytorch as smp
import albumentations as A
from albumentations.pytorch import ToTensorV2
from datetime import datetime

# ===================== CONFIGURATION =====================
MODEL_PATH = "models/best_model.pth"
OUTPUT_DIR = "output"
IMG_SIZE = 512
THRESHOLD = 0.5

# Normalization bounds (must match training)
MIN_BT = 180.0
MAX_BT = 320.0

# Device
DEVICE = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"


# ===================== MODEL =====================
def load_model(model_path: str):
    """Load trained U-Net model."""
    model = smp.Unet(
        encoder_name="mobilenet_v2",
        encoder_weights=None,
        in_channels=1,
        classes=1,
    )
    model.load_state_dict(torch.load(model_path, map_location=DEVICE, weights_only=True))
    model.to(DEVICE)
    model.eval()
    return model


# ===================== PREPROCESSING =====================
def load_h5_data(h5_path: str):
    """
    Load INSAT-3D H5 file.
    Returns: irbt_array, lat_grid, lon_grid
    """
    with h5py.File(h5_path, 'r') as f:
        # IRBT
        raw_counts = f['IMG_TIR1'][0]
        lut = f['IMG_TIR1_TEMP'][:]
        irbt = lut[raw_counts].astype(np.float32)
        
        # Coordinates
        lat = f['Latitude'][:].astype(np.float32)
        lon = f['Longitude'][:].astype(np.float32)
    
    return irbt, lat, lon


def preprocess(irbt: np.ndarray):
    """
    Normalize and transform for model input.
    Returns: torch tensor [1, 1, H, W]
    """
    # Normalize to [0, 1]
    normalized = (irbt - MIN_BT) / (MAX_BT - MIN_BT)
    normalized = np.clip(normalized, 0, 1).astype(np.float32)
    
    # Resize and convert to tensor
    transform = A.Compose([
        A.Resize(IMG_SIZE, IMG_SIZE),
        ToTensorV2()
    ])
    
    tensor = transform(image=normalized)['image']  # [1, H, W]
    return tensor.unsqueeze(0)  # [1, 1, H, W]


# ===================== INFERENCE =====================
def run_inference(model, tensor):
    """
    Run model inference.
    Returns: probability_map, binary_mask (both at IMG_SIZE resolution)
    """
    tensor = tensor.to(DEVICE)
    
    with torch.no_grad():
        output = model(tensor)
        prob = torch.sigmoid(output).squeeze().cpu().numpy()
    
    mask = (prob > THRESHOLD).astype(np.uint8)
    return prob, mask


# ===================== OUTPUTS =====================
def save_mask_npy(mask: np.ndarray, output_path: str):
    """Save binary mask as .npy"""
    np.save(output_path, mask)
    print(f"[SAVED] {output_path}")


def save_mask_png(mask: np.ndarray, output_path: str):
    """Save visual mask as .png"""
    plt.figure(figsize=(8, 8))
    plt.imshow(mask, cmap='gray')
    plt.axis('off')
    plt.tight_layout(pad=0)
    plt.savefig(output_path, bbox_inches='tight', pad_inches=0, dpi=150)
    plt.close()
    print(f"[SAVED] {output_path}")


def save_netcdf(irbt: np.ndarray, 
                prob: np.ndarray, 
                mask: np.ndarray,
                lat: np.ndarray, 
                lon: np.ndarray,
                timestamp: datetime,
                output_path: str):
    """
    Save NetCDF with CF-compliant structure.
    
    Dimensions: time, lat, lon
    Variables: irbt, tcc_probability, tcc_mask
    """
    # Resize probability and mask to original resolution
    h, w = irbt.shape
    prob_resized = cv2.resize(prob, (w, h), interpolation=cv2.INTER_LINEAR)
    mask_resized = cv2.resize(mask.astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST).astype(np.uint8)
    
    # Create xarray Dataset
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
                "units": "degrees_north",
                "standard_name": "latitude"
            }),
            "longitude": (["lat", "lon"], lon, {
                "long_name": "Longitude", 
                "units": "degrees_east",
                "standard_name": "longitude"
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
    
    # Save
    ds.to_netcdf(output_path, engine="netcdf4")
    print(f"[SAVED] {output_path}")


# ===================== MAIN PIPELINE =====================
def extract_timestamp(h5_path: str) -> datetime:
    """Extract timestamp from H5 filename."""
    basename = os.path.basename(h5_path)
    # Pattern: 3RIMG_01JAN2024_0015_L1B_STD_V01R00.h5
    try:
        parts = basename.split('_')
        date_str = parts[1]  # 01JAN2024
        time_str = parts[2]  # 0015
        dt = datetime.strptime(f"{date_str}_{time_str}", "%d%b%Y_%H%M")
        return dt
    except:
        return datetime.now()


def find_h5_files(data_dir: str = "MOSDAC_Data") -> list:
    """Find all .h5 files in MOSDAC download directory."""
    patterns = [
        os.path.join(data_dir, "**", "*.h5"),
        os.path.join(data_dir, "*.h5"),
    ]
    
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern, recursive=True))
    
    return sorted(set(files))


def process_file(model, h5_path: str, output_dir: str):
    """Process single H5 file and generate 3 outputs."""
    
    # Extract timestamp for naming
    timestamp = extract_timestamp(h5_path)
    ts_str = timestamp.strftime("%Y%m%d_%H%M")
    
    # Create output subdirectory
    file_output_dir = os.path.join(output_dir, ts_str)
    os.makedirs(file_output_dir, exist_ok=True)
    
    print(f"\n[PROCESSING] {os.path.basename(h5_path)}")
    
    # Step 1: Load data
    irbt, lat, lon = load_h5_data(h5_path)
    print(f"  IRBT shape: {irbt.shape}")
    
    # Step 2: Preprocess
    tensor = preprocess(irbt)
    
    # Step 3: Inference
    prob, mask = run_inference(model, tensor)
    print(f"  TCC pixels detected: {np.sum(mask)}")
    
    # Step 4: Save outputs
    save_mask_npy(mask, os.path.join(file_output_dir, "mask.npy"))
    save_mask_png(mask, os.path.join(file_output_dir, "mask.png"))
    save_netcdf(irbt, prob, mask, lat, lon, timestamp, os.path.join(file_output_dir, "output.nc"))
    
    return file_output_dir


def run_mosdac_download():
    """Run MOSDAC API download (calls mdapi.py)."""
    import subprocess
    
    print("\n" + "="*50)
    print("STEP 1: MOSDAC DATA DOWNLOAD")
    print("="*50)
    
    # Check if mdapi.py exists
    mdapi_paths = [
        "mdapi.py",
        "backend/mosdac_engine/mdapi.py",
    ]
    
    mdapi_path = None
    for p in mdapi_paths:
        if os.path.exists(p):
            mdapi_path = p
            break
    
    if mdapi_path is None:
        print("[SKIP] mdapi.py not found. Using existing data in MOSDAC_Data/")
        return
    
    # Run download
    print(f"[RUN] python {mdapi_path}")
    result = subprocess.run(["python", mdapi_path], capture_output=False)
    
    if result.returncode != 0:
        print("[WARNING] MOSDAC download may have issues. Continuing with existing data...")


def main():
    """Main pipeline entry point."""
    
    print("\n" + "="*60)
    print("  CloudSense TCC Inference Pipeline")
    print("="*60)
    
    # Step 1: Download data (optional - uses existing if mdapi.py not found)
    run_mosdac_download()
    
    # Step 2: Find H5 files
    print("\n" + "="*50)
    print("STEP 2: FINDING H5 FILES")
    print("="*50)
    
    h5_files = find_h5_files()
    
    if not h5_files:
        print("[ERROR] No H5 files found in MOSDAC_Data/")
        return
    
    print(f"Found {len(h5_files)} H5 file(s)")
    
    # Step 3: Load model
    print("\n" + "="*50)
    print("STEP 3: LOADING MODEL")
    print("="*50)
    
    if not os.path.exists(MODEL_PATH):
        print(f"[ERROR] Model not found: {MODEL_PATH}")
        return
    
    model = load_model(MODEL_PATH)
    print(f"Model loaded on {DEVICE}")
    
    # Step 4: Process each file
    print("\n" + "="*50)
    print("STEP 4: RUNNING INFERENCE")
    print("="*50)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    for h5_path in h5_files:
        try:
            process_file(model, h5_path, OUTPUT_DIR)
        except Exception as e:
            print(f"[ERROR] Failed to process {h5_path}: {e}")
    
    print("\n" + "="*60)
    print("  PIPELINE COMPLETE")
    print(f"  Outputs saved to: {os.path.abspath(OUTPUT_DIR)}/")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
