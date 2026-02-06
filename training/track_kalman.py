
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
OUTPUT_CSV = "trajectory_kalman.csv"
OUTPUT_PLOT = "cyclone_trajectory_smoothed.png"
IMG_SIZE = 512
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
GATING_THRESHOLD = 60.0 # Pixels (approx 240km). Reject jumps larger than this.

def get_transforms():
    return A.Compose([
        A.Resize(IMG_SIZE, IMG_SIZE),
        ToTensorV2()
    ])

def load_model():
    model = smp.Unet(
        encoder_name="mobilenet_v2",
        encoder_weights=None,
        in_channels=1,
        classes=1,
    )
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
    model.to(DEVICE)
    model.eval()
    return model

def preprocess_image(h5_path):
    try:
        with h5py.File(h5_path, 'r') as f:
            raw = f['IMG_TIR1'][0]
            lut = f['IMG_TIR1_TEMP'][:]
            img = lut[raw]
        min_bt, max_bt = 180.0, 320.0
        img = (img - min_bt) / (max_bt - min_bt)
        img = np.clip(img, 0, 1).astype(np.float32)
        tf = get_transforms()
        return tf(image=img)['image'].unsqueeze(0)
    except Exception:
        return None

def find_centroid(mask_pred):
    mask_uint8 = (mask_pred * 255).astype(np.uint8)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask_uint8, connectivity=8)
    if num_labels <= 1:
        return None
    largest_label = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    return centroids[largest_label] # (cx, cy)

class CycloneTracker:
    def __init__(self):
        # 4 dynamic params (x, y, dx, dy), 2 measurement params (x, y)
        self.kf = cv2.KalmanFilter(4, 2)
        self.kf.measurementMatrix = np.array([[1, 0, 0, 0], 
                                              [0, 1, 0, 0]], np.float32)
        self.kf.transitionMatrix = np.array([[1, 0, 1, 0], 
                                             [0, 1, 0, 1], 
                                             [0, 0, 1, 0], 
                                             [0, 0, 0, 1]], np.float32)
        self.kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.03 # Lower = smoother
        self.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 1.0 # Trust measurement
        self.first_frame = True
        
    def update(self, measured_point):
        """
        measured_point: (x, y) or None
        Returns: (filtered_x, filtered_y), is_predicted
        """
        # 1. Prediction
        prediction = self.kf.predict() # Returns (x, y, dx, dy)
        pred_x, pred_y = prediction[0, 0], prediction[1, 0]
        
        if self.first_frame:
            if measured_point is not None:
                # Initialize state
                self.kf.statePost = np.array([[measured_point[0]], [measured_point[1]], [0], [0]], dtype=np.float32)
                self.first_frame = False
                return measured_point, False
            else:
                return None, True

        if measured_point is None:
            # Missing observation: Trust prediction
            # We can feed the prediction back as measurement? Or just skip correction.
            # Standard: Skip correction. State remains as Predicted.
            return (pred_x, pred_y), True
            
        # 2. Gating
        mx, my = measured_point
        dist = np.sqrt((mx - pred_x)**2 + (my - pred_y)**2)
        
        if dist > GATING_THRESHOLD:
            # Outlier / Fragmentation Jump
            # Reject measurement, use prediction
            # print(f"Outlier detected: dist={dist:.1f}")
            return (pred_x, pred_y), True
        else:
            # Valid measurement
            meas_array = np.array([[np.float32(mx)], [np.float32(my)]])
            self.kf.correct(meas_array)
            # Return corrected state
            filtered = self.kf.statePost
            return (filtered[0, 0], filtered[1, 0]), False

def main():
    if not os.path.exists(MODEL_PATH):
        return
    model = load_model()
    
    with open(INDEX_FILE, 'r') as f:
        entries = json.load(f)
    entries.sort(key=lambda x: x['timestamp'])
    
    tracker = CycloneTracker()
    trajectory = []
    
    raw_x, raw_y = [], []
    smooth_x, smooth_y = [], []
    
    print(f"Tracking with Kalman Filter across {len(entries)} frames...")
    
    for entry in tqdm(entries):
        ts = entry['timestamp']
        
        # Inference
        img_tensor = preprocess_image(entry['h5_path'])
        centroid = None
        
        if img_tensor is not None:
            img_tensor = img_tensor.to(DEVICE)
            with torch.no_grad():
                output = model(img_tensor)
                prob = torch.sigmoid(output).squeeze().cpu().numpy()
            mask = (prob > 0.5).astype(np.uint8)
            centroid = find_centroid(mask)
            
        # Update Tracker
        filtered_pos, is_predicted = tracker.update(centroid)
        
        # Store Data
        if centroid is not None:
            raw_x.append(centroid[0])
            raw_y.append(centroid[1])
        else:
            raw_x.append(np.nan)
            raw_y.append(np.nan)
            
        if filtered_pos is not None:
            smooth_x.append(filtered_pos[0])
            smooth_y.append(filtered_pos[1])
            trajectory.append({
                "timestamp": ts,
                "smooth_cx": filtered_pos[0],
                "smooth_cy": filtered_pos[1],
                "is_predicted": is_predicted,
                "raw_cx": centroid[0] if centroid is not None else None,
                "raw_cy": centroid[1] if centroid is not None else None
            })
            
    # Save CSV
    df = pd.DataFrame(trajectory)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Smoothed trajectory saved to {OUTPUT_CSV}")
    
    # Plot
    plt.figure(figsize=(10, 10))
    # Invert Y for image coords
    
    # Plot Raw
    plt.plot(raw_x, raw_y, 'r.', markersize=2, alpha=0.3, label='Raw Detections')
    
    # Plot Smooth
    plt.plot(smooth_x, smooth_y, 'g-', linewidth=2, label='Kalman Smoothed')
    
    # Highlight Predicted (Gated) segments?
    # Keeping it simple for now.
    
    plt.xlim(0, 512)
    plt.ylim(512, 0)
    plt.title("Cyclone Trajectory: Raw vs Kalman Smoothed")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(OUTPUT_PLOT)
    print(f"Plot saved to {OUTPUT_PLOT}")

if __name__ == "__main__":
    main()
