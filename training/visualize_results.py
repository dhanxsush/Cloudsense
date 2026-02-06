
import os
import json
import torch
import numpy as np
import matplotlib.pyplot as plt
import segmentation_models_pytorch as smp
import h5py
import albumentations as A
from albumentations.pytorch import ToTensorV2
import random

# Configuration
INDEX_FILE = "dataset_index_labeled.json"
MODEL_PATH = "models/best_model.pth"
OUTPUT_IMG = "validation_gallery.png"
IMG_SIZE = 512
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

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

def load_sample(entry):
    h5_path = entry['h5_path']
    mask_path = entry['mask_path']
    
    # Load Image
    with h5py.File(h5_path, 'r') as f:
        raw = f['IMG_TIR1'][0]
        lut = f['IMG_TIR1_TEMP'][:]
        img = lut[raw]
        
    # Normalize
    img = (img - 180.0) / (320.0 - 180.0)
    img = np.clip(img, 0, 1).astype(np.float32)
    
    # Load Mask
    mask = np.load(mask_path).astype(np.float32)
    
    # Transform
    tf = A.Compose([A.Resize(IMG_SIZE, IMG_SIZE), ToTensorV2()])
    augmented = tf(image=img, mask=mask)
    
    return augmented['image'], augmented['mask']

def main():
    print("Generating Validation Gallery...")
    
    # Load Index
    with open(INDEX_FILE, 'r') as f:
        entries = json.load(f)
    entries.sort(key=lambda x: x['timestamp'])
    
    # Validation Split (Last 20%)
    split_idx = int(0.8 * len(entries))
    val_entries = entries[split_idx:]
    
    # Select 5 random samples
    samples = random.sample(val_entries, 5)
    
    model = load_model()
    
    fig, axes = plt.subplots(5, 3, figsize=(12, 20))
    # fig.suptitle("Model Validation: Input | Ground Truth | Prediction", fontsize=16)
    
    cols = ["Input IR", "Pseudo-Label (Truth)", "Model Prediction"]
    for ax, col in zip(axes[0], cols):
        ax.set_title(col)
        
    for i, entry in enumerate(samples):
        img_tensor, mask_tensor = load_sample(entry)
        
        # Inference
        input_batch = img_tensor.unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            out = model(input_batch)
            prob = torch.sigmoid(out).squeeze().cpu().numpy()
            
        pred_mask = (prob > 0.5).astype(np.uint8)
        
        # Plot
        # 1. Input
        img_np = img_tensor.squeeze().numpy()
        axes[i, 0].imshow(img_np, cmap='jet_r')
        axes[i, 0].axis('off')
        axes[i, 0].text(5, 20, entry['timestamp'], color='white', fontweight='bold')
        
        # 2. Ground Truth
        axes[i, 1].imshow(mask_tensor.squeeze().numpy(), cmap='gray')
        axes[i, 1].axis('off')
        
        # 3. Prediction
        axes[i, 2].imshow(pred_mask, cmap='gray')
        axes[i, 2].axis('off')
        
        # Highlight Dice Score for this sample
        intersection = np.sum((pred_mask * mask_tensor.squeeze().numpy()))
        union = np.sum(pred_mask) + np.sum(mask_tensor.squeeze().numpy())
        dice = (2. * intersection) / (union + 1e-6)
        axes[i, 2].text(5, 450, f"Dice: {dice:.2f}", color='lime', fontweight='bold', fontsize=12)

    plt.tight_layout()
    plt.savefig(OUTPUT_IMG)
    print(f"Gallery saved to {OUTPUT_IMG}")

if __name__ == "__main__":
    main()
