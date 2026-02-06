
import os
import glob
import h5py
import json
import re
from datetime import datetime
import pandas as pd
from typing import Dict, List, Optional

# Configuration
DATASET_ROOT = "/Users/dhanush/Downloads/Michaung_Data/Nov25_162336"
H5_ROOT = os.path.join(DATASET_ROOT, "h5 files")
IMAGE_ROOT = os.path.join(DATASET_ROOT, "images")
OUTPUT_FILE = "dataset_index.json"

def parse_timestamp(filename: str) -> Optional[str]:
    """
    Extracts timestamp from filename.
    Expected format: 3RIMG_01DEC2023_0015_...
    Returns: YYYYMMDD_HHMM string or None
    """
    # Regex to match DDMMMYYYY_HHMM (e.g., 01DEC2023_0015)
    match = re.search(r"(\d{2}[A-Z]{3}\d{4}_\d{4})", filename)
    if match:
        raw_ts = match.group(1)
        try:
            # Parse to datetime to normalize format
            dt = datetime.strptime(raw_ts, "%d%b%Y_%H%M")
            return dt.strftime("%Y%m%d_%H%M")
        except ValueError:
            return None
    return None

def scan_files(root_dir: str, extension: str) -> Dict[str, str]:
    """
    Recursively scans for files with given extension.
    Returns: Dict[timestamp, absolute_path]
    """
    files_map = {}
    print(f"Scanning {root_dir} for {extension}...")
    
    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            if f.endswith(extension):
                # We need to handle the specific image naming convention which might produce duplicates if we aren't careful?
                # Actually, images are distinct by band in the filename?
                # Based on file listing: 3RIMG_01DEC2023_0015_L1C_ASIA_MER_IR1_V01R00.jpg
                # The H5 files seem to be just one per timestamp?
                # Let's check matching.
                
                # For images, we just want to know if *any* visualization exists, or maybe a specific one.
                # The user requirement says "Map .h5 -> image".
                # Let's map timestamp to the FIRST image found for that timestamp for now,
                # or a list of images.
                
                ts = parse_timestamp(f)
                if ts:
                    full_path = os.path.join(dirpath, f)
                    if ts not in files_map:
                        files_map[ts] = []
                    files_map[ts].append(full_path)
    
    # For H5, we expect one per timestamp
    if extension == ".h5":
        # Flatten list if sure it's 1:1, but safety first
        # Looking at listings: 3RIMG_01DEC2023_0015_L1C_ASIA_MER_V01R00.h5
        # Yes, looks like one file per slot.
        return {k: v[0] for k, v in files_map.items()} 
        
    return files_map

def validate_h5(file_path: str) -> Dict:
    """
    Opens H5 file and extracts basic metadata/checks integrity.
    """
    try:
        with h5py.File(file_path, 'r') as f:
            # We look for the main thermal band, typically 'IMG_TIR1' or similar for INSAT
            # If we don't know the exact key, we can list keys.
            # Based on common INSAT structure, usually 'IMG_TIR1' is the IR band.
            # But let's just inspect the keys available.
            
            keys = list(f.keys())
            
            # Heuristic: Find a dataset that looks like image data
            # Often 'IMG_TIR1', 'IMG_MIR', etc.
            # We want IR1 typically for TCC.
            
            target_band = 'IMG_TIR1'
            if target_band not in keys:
                # Fallback or check what IS there
                # For now just record keys
                return {"valid": False, "error": f"Missing {target_band}", "keys": keys}
            
            data_shape = f[target_band].shape
            
            # Simple integrity check: non-zero shape
            if data_shape[0] == 0 or data_shape[1] == 0:
                 return {"valid": False, "error": "Empty shape"}

            return {
                "valid": True,
                "shape": data_shape,
                "keys": keys
            }
            
    except Exception as e:
        return {"valid": False, "error": str(e)}

def main():
    print("Starting Dataset Audit...")
    
    # 1. Scan H5 files
    h5_map = scan_files(H5_ROOT, ".h5")
    print(f"Found {len(h5_map)} H5 files.")
    
    # 2. Scan Image files
    img_map = scan_files(IMAGE_ROOT, ".jpg") # Listing showed .jpg
    print(f"Found images for {len(img_map)} timestamps.")
    
    # 3. Match and Validate
    dataset_index = []
    
    # Sort by timestamp
    sorted_timestamps = sorted(h5_map.keys())
    
    print("\nValidating files...")
    for ts in sorted_timestamps:
        h5_path = h5_map[ts]
        
        # Validation
        val_res = validate_h5(h5_path)
        
        entry = {
            "timestamp": ts,
            "h5_path": h5_path,
            "image_paths": img_map.get(ts, []),
            "h5_valid": val_res.get("valid", False),
            "h5_shape": val_res.get("shape", None),
            "h5_keys": val_res.get("keys", []),
            "error": val_res.get("error", None)
        }
        
        dataset_index.append(entry)
        
    # 4. Save Output
    print(f"\nWriting manifest to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(dataset_index, f, indent=2)
        
    # 5. Summary Stats
    df = pd.DataFrame(dataset_index)
    print("\n--- Audit Summary ---")
    print(f"Total Entries: {len(df)}")
    print(f"Valid H5 Files: {df['h5_valid'].sum()}")
    print(f"Entries with Images: {df['image_paths'].apply(len).gt(0).sum()}")
    
    if len(df) > 0 and 'h5_shape' in df.columns:
         print(f"Unique Shapes: {df['h5_shape'].astype(str).unique()}")
    
    print("Done.")

if __name__ == "__main__":
    main()
