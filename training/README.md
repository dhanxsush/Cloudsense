# Training: Dataset & Model Training

## Overview
This folder contains the historical Michaung cyclone dataset and all training/analysis scripts.

**Purpose:** Train the U-Net model for cloud detection  
**Dataset:** INSAT-3DR satellite imagery (Nov-Dec 2023)  
**Size:** ~1900 HDF5 files

---

## Contents

```
training/
├── data/
│   └── raw/              # HDF5 satellite images
├── models/               # Training outputs
│   └── best_model.pth   # Best trained weights
├── train_model.py        # Main training script
├── track_kalman.py       # Trajectory analysis
├── generate_labels.py    # Label generation
├── dataset_audit.py      # Data validation
└── dataset_index_labeled.json  # Training index
```

---

## Usage

### Training a New Model
```bash
cd training
python train_model.py
```

**Output:**
- `models/best_model.pth` - Trained weights
- Training logs and metrics

### Analyzing Trajectories
```bash
python track_kalman.py
```

**Output:**
- `trajectory_kalman.csv` - Smoothed trajectory
- `cyclone_trajectory_smoothed.png` - Visualization

---

## Dataset

**Source:** ISRO/MOSDAC (INSAT-3DR)  
**Event:** Cyclone Michaung (November-December 2023)  
**Format:** HDF5 files with thermal infrared data  
**Coverage:** Bay of Bengal region

**File Naming:**
```
INSAT3D_TIR1_YYYYMMDD_HHMM.h5
```

---

## Connection to Other Modules

### Training → Models
After training completes:
```bash
# Copy trained weights to models folder
cp models/best_model.pth ../models/
```

### Models → Backend
Backend uses the trained model:
```python
# backend/analysis_engine.py
MODEL_PATH = "../models/best_model.pth"
```

---

## Note

⚠️ **This folder is NOT required to run the application.**

It's only needed if you want to:
- Retrain the model
- Analyze historical data
- Generate new labels

For running the app, you only need `frontend/`, `backend/`, and `models/`.
