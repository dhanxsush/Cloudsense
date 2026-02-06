import os
import json
import h5py
import numpy as np
from sklearn.cluster import DBSCAN
import matplotlib.pyplot as plt
from tqdm import tqdm
import argparse

# Configuration
INPUT_INDEX = "dataset_index.json"
OUTPUT_MASK_DIR = "masks"
OUTPUT_VIS_DIR = "vis"
BT_THRESHOLD = 218.0  # Kelvin
PIXEL_AREA_KM2 = 16.0 # Approx 4km x 4km
MIN_AREA_KM2 = 34800.0

# DBSCAN Params
# We are clustering on pixel coordinates (row, col) transformed to some distance metric?
# Or just simple grid distance.
# Grid distance: 1 unit = 4km.
# Radius 111km constraint is mentioned in PRD.
# 111km / 4km/pixel = 27.75 pixels.
# Let's be lenient for DBSCAN eps. 
# PRD says "Radius >= 111 km" as a CONSTRAINT, usually implying the size of the system.
# DBSCAN eps usually defines "connectivity" distance.
# For continuous cloud systems, pixels should be adjacent.
# eps=1.5 (Chebyshev or Euclidean adjacency) is standard for raster segmentation.
DBSCAN_EPS = 1.5 
DBSCAN_MIN_SAMPLES = 5 # Minimum pixels to form a core point (noise reduction)

def load_data(h5_path):
    """Loads IRBT counts and LUT, returns calibrated BT array."""
    with h5py.File(h5_path, 'r') as f:
        # Load raw counts (10-bit)
        # Note: Shape is (1, H, W). Squeeze to (H, W)
        raw_counts = f['IMG_TIR1'][0]
        
        # Load LUT
        lut = f['IMG_TIR1_TEMP'][:]
        
        # Calibration
        # Vectorised lookup
        bt_array = lut[raw_counts]
        
        return bt_array

def generate_mask(bt_array):
    """
    Generates binary mask for TCCs.
    1. Threshold < 218K
    2. DBSCAN Clustering
    3. Area filtering
    """
    H, W = bt_array.shape
    
    # 1. Threshold
    # Note: Invalid pixels might have high temp or NaN.
    # Check for NaN just in case, though standard int lookup usually shouldn't produce nan unless in LUT.
    
    potential_cloud_mask = (bt_array < BT_THRESHOLD)
    
    if not np.any(potential_cloud_mask):
        return np.zeros((H, W), dtype=np.uint8)
    
    # 2. Extract coordinates of candidate pixels
    # (row, col)
    # y = dims[0], x = dims[1]
    y_idxs, x_idxs = np.where(potential_cloud_mask)
    
    # Stack for clustering
    # Shape (N, 2)
    coords = np.column_stack((y_idxs, x_idxs))
    
    if len(coords) == 0:
        return np.zeros((H, W), dtype=np.uint8)
        
    # 3. DBSCAN
    # We use a relatively small eps because we want connected components in the grid.
    # Eps=sqrt(2) approx 1.42 covers diagonals. 1.5 is safe.
    db = DBSCAN(eps=DBSCAN_EPS, min_samples=DBSCAN_MIN_SAMPLES, metric='euclidean', n_jobs=-1)
    labels = db.fit_predict(coords)
    
    # 4. Filter Clusters by Area
    final_mask = np.zeros((H, W), dtype=np.uint8)
    
    unique_labels = set(labels)
    if -1 in unique_labels:
        unique_labels.remove(-1) # Remove noise
        
    for lbl in unique_labels:
        # Count pixels in this cluster
        cluster_mask = (labels == lbl)
        pixel_count = np.sum(cluster_mask)
        
        area_km2 = pixel_count * PIXEL_AREA_KM2
        
        if area_km2 >= MIN_AREA_KM2:
            # Add to final mask
            # Get coords for this label
            cluster_coords = coords[cluster_mask]
            final_mask[cluster_coords[:, 0], cluster_coords[:, 1]] = 1
            
    return final_mask

def save_vis(bt_array, mask, timestamp, output_dir):
    """Saves a side-by-side visualization."""
    fig, ax = plt.subplots(1, 2, figsize=(12, 6))
    
    # IR Image
    im1 = ax[0].imshow(bt_array, cmap='jet_r', vmin=180, vmax=320)
    ax[0].set_title(f"IR Brightness Temp ({timestamp})")
    plt.colorbar(im1, ax=ax[0], fraction=0.046, pad=0.04)
    
    # Mask
    ax[1].imshow(mask, cmap='gray')
    ax[1].set_title(f"TCC Mask (> {int(MIN_AREA_KM2)} km²)")
    
    plt.tight_layout()
    out_path = os.path.join(output_dir, f"vis_{timestamp}.png")
    plt.savefig(out_path)
    plt.close()

def main():
    # Setup
    os.makedirs(OUTPUT_MASK_DIR, exist_ok=True)
    os.makedirs(OUTPUT_VIS_DIR, exist_ok=True)
    
    # Load Index
    with open(INPUT_INDEX, 'r') as f:
        dataset_index = json.load(f)
        
    print(f"Processing {len(dataset_index)} samples...")
    
    updated_index = []
    
    # Progress Bar
    for entry in tqdm(dataset_index):
        ts = entry['timestamp']
        h5_path = entry['h5_path']
        
        try:
            # 1. Load & Calibrate
            bt_array = load_data(h5_path)
            
            # 2. Generate Mask
            mask = generate_mask(bt_array)
            
            # 3. Save Mask
            mask_filename = f"{ts}.npy"
            mask_path = os.path.join(OUTPUT_MASK_DIR, mask_filename)
            np.save(mask_path, mask)
            
            # 4. Visualize (Sample every 10th or if mask is non-empty?)
            # Let's visualize if mask has ANY cloud, to verify positive cases.
            # And maybe a few negatives.
            if np.sum(mask) > 0:
                # Limit visualizations to avoid spamming disk
                # Check if vis file exists? Or just overwrite.
                # Let's do first 5 positives + sampling.
                vis_path = os.path.join(OUTPUT_VIS_DIR, f"vis_{ts}.png")
                # For now, generate visualization for ALL positive detections to verify tracking continuity later.
                save_vis(bt_array, mask, ts, OUTPUT_VIS_DIR)
            
            # 5. Update Index
            entry['mask_path'] = os.path.abspath(mask_path)
            entry['has_tcc'] = bool(np.sum(mask) > 0)
            updated_index.append(entry)
            
        except Exception as e:
            print(f"Error processing {ts}: {e}")
            entry['error_phase2'] = str(e)
            updated_index.append(entry)
            
    # Save updated index
    with open("dataset_index_labeled.json", 'w') as f:
        json.dump(updated_index, f, indent=2)
        
    print("\nProcessing Complete.")
    print(f"Labeled index saved to dataset_index_labeled.json")
    
    # Stats
    n_positive = sum(1 for e in updated_index if e.get('has_tcc', False))
    print(f"Samples with TCCs detected: {n_positive} / {len(updated_index)}")

if __name__ == "__main__":
    main()
