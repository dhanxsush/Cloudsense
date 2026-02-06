
import os
import json
import h5py
import numpy as np
import torch
import cv2
import pandas as pd
import matplotlib.pyplot as plt
import segmentation_models_pytorch as smp
import albumentations as A
from albumentations.pytorch import ToTensorV2
from tqdm import tqdm

# Configuration
INDEX_FILE = "dataset_index_labeled.json"
MODEL_PATH = "models/best_model.pth"
OUTPUT_CSV = "trajectory_data.csv"
OUTPUT_PLOT = "cyclone_trajectory.png"
IMG_SIZE = 512
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

print(f"Using device: {DEVICE}")

def get_transforms():
    return A.Compose([
        A.Resize(IMG_SIZE, IMG_SIZE),
        ToTensorV2()
    ])

def load_model():
    model = smp.Unet(
        encoder_name="mobilenet_v2",
        encoder_weights=None, # We are loading custom weights
        in_channels=1,
        classes=1,
    )
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
    model.to(DEVICE)
    model.eval()
    return model

def preprocess_image(h5_path):
    """
    Reads H5, Validates, Calibrates, Normalizes.
    Returns: Tensor [1, C, H, W] (batch dim added)
    """
    try:
        with h5py.File(h5_path, 'r') as f:
            raw = f['IMG_TIR1'][0]
            lut = f['IMG_TIR1_TEMP'][:]
            # Calibration
            img = lut[raw]
            
        # Normalize (Same as training)
        min_bt = 180.0
        max_bt = 320.0
        img = (img - min_bt) / (max_bt - min_bt)
        img = np.clip(img, 0, 1).astype(np.float32)
        
        # Transform
        tf = get_transforms()
        tensor = tf(image=img)['image'].unsqueeze(0) # Add batch dim
        return tensor
        
    except Exception as e:
        print(f"Error reading {h5_path}: {e}")
        return None

def find_centroid(mask_pred):
    """
    Finds centroid of the largest connected component in the binary mask.
    mask_pred: 512x512 numpy array (0 or 1)
    """
    # 1. Connected Components
    # Ensure uint8
    mask_uint8 = (mask_pred * 255).astype(np.uint8)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask_uint8, connectivity=8)
    
    if num_labels <= 1:
        return None, 0 # Background only
        
    # 2. Find Largest Component (Format: [x, y, w, h, area])
    # Skip label 0 (background)
    largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    largest_area = stats[largest_label, cv2.CC_STAT_AREA]
    
    # 3. Get Centroid
    cx, cy = centroids[largest_label]
    
    return (cx, cy), largest_area

def main():
    # Load Model
    if not os.path.exists(MODEL_PATH):
        print(f"Model not found at {MODEL_PATH}")
        return
        
    model = load_model()
    
    # Load Data Index
    with open(INDEX_FILE, 'r') as f:
        entries = json.load(f)
        
    # Sort chronologically
    entries.sort(key=lambda x: x['timestamp'])
    
    trajectory = []
    
    print(f"Tracking Cyclone across {len(entries)} frames...")
    
    for entry in tqdm(entries):
        ts = entry['timestamp']
        h5_path = entry['h5_path']
        
        # Inference
        img_tensor = preprocess_image(h5_path)
        if img_tensor is None:
            continue
            
        img_tensor = img_tensor.to(DEVICE)
        
        with torch.no_grad():
            output = model(img_tensor)
            prob = torch.sigmoid(output).squeeze().cpu().numpy()
            
        # Threshold
        mask = (prob > 0.5).astype(np.uint8)
        
        # Analysis
        centroid, area = find_centroid(mask)
        
        if centroid:
            cx, cy = centroid
            trajectory.append({
                "timestamp": ts,
                "cx": cx,
                "cy": cy,
                "area_pixels_512": area
            })
            
    # Save Data
    df = pd.DataFrame(trajectory)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Trajectory data saved to {OUTPUT_CSV}")
    
    # Visualization
    if len(df) > 0:
        plt.figure(figsize=(10, 10))
        # Invert Y because image coords (0,0) is Top-Left, usually plots are Bottom-Left
        # But for 'Image' view, we want (0,0) at Top-Left.
        
        plt.plot(df['cx'], df['cy'], 'r.-', linewidth=1, markersize=3, label='Centroid Path')
        
        # Mark Start and End
        plt.plot(df.iloc[0]['cx'], df.iloc[0]['cy'], 'go', markersize=10, label='Start')
        plt.plot(df.iloc[-1]['cx'], df.iloc[-1]['cy'], 'bo', markersize=10, label='End')
        
        plt.xlim(0, 512)
        plt.ylim(512, 0) # Invert Y axis to match image coordinates
        plt.title("Estimated Cyclone Michaung Trajectory (512x512 Grid)")
        plt.xlabel("X (Pixels)")
        plt.ylabel("Y (Pixels)")
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.savefig(OUTPUT_PLOT)
        print(f"Trajectory plot saved to {OUTPUT_PLOT}")
    else:
        print("No valid centroids tracking.")

if __name__ == "__main__":
    main()
