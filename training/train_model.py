import os
import json
import h5py
import numpy as np
import torch
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import segmentation_models_pytorch as smp
import cv2
from tqdm import tqdm
import albumentations as A
from albumentations.pytorch import ToTensorV2

# Configuration
INDEX_FILE = "dataset_index_labeled.json"
MODEL_DIR = "models"
IMG_SIZE = 512
BATCH_SIZE = 8 # Adjust based on GPU memory. Apple Silicon Unified Memory usually handles this nicely.
EPOCHS = 10 
LR = 1e-4
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

print(f"Using device: {DEVICE}")

class MichaungDataset(Dataset):
    def __init__(self, entries, transform=None):
        self.entries = entries
        self.transform = transform
        
    def __len__(self):
        return len(self.entries)
    
    def __getitem__(self, idx):
        entry = self.entries[idx]
        h5_path = entry['h5_path']
        mask_path = entry['mask_path']
        
        # 1. Load Image (IRBT)
        with h5py.File(h5_path, 'r') as f:
            raw_counts = f['IMG_TIR1'][0]
            lut = f['IMG_TIR1_TEMP'][:]
            image = lut[raw_counts]
            
        # 2. Normalize Image
        # Range approx 180K to 320K.
        # Min-max normalization to [0, 1]
        # Using fixed physics bounds for consistency
        min_bt = 180.0
        max_bt = 320.0
        image = (image - min_bt) / (max_bt - min_bt)
        image = np.clip(image, 0, 1).astype(np.float32)
        
        # 3. Load Mask
        mask = np.load(mask_path).astype(np.float32)
        
        # 4. Transform (Resize, Augment, ToTensor)
        if self.transform:
            augmented = self.transform(image=image, mask=mask)
            image = augmented['image']
            mask = augmented['mask']
            
        return image, mask

def get_transforms(stage='train'):
    if stage == 'train':
        return A.Compose([
            A.Resize(IMG_SIZE, IMG_SIZE),
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.5), # Clouds don't have up/down orientation
            A.Rotate(limit=30, p=0.5),
            ToTensorV2()
        ])
    else:
        return A.Compose([
            A.Resize(IMG_SIZE, IMG_SIZE),
            ToTensorV2()
        ])

def train_epoch(model, loader, criterion, optimizer, scaler):
    model.train()
    total_loss = 0
    
    for images, masks in tqdm(loader, desc="Training"):
        images = images.to(DEVICE)
        masks = masks.to(DEVICE).unsqueeze(1) # [B, 1, H, W]
        
        optimizer.zero_grad()
        
        # Mixed precision for speed if possible (MPS doesn't support autocast fully yet like CUDA, check pytorch docs)
        # We'll stick to standard FP32 for MPS stability unless needed.
        outputs = model(images)
        loss = criterion(outputs, masks)
        
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item()
        
    return total_loss / len(loader)

def validate(model, loader, criterion):
    model.eval()
    total_loss = 0
    total_iou = 0
    
    with torch.no_grad():
        for images, masks in tqdm(loader, desc="Validation"):
            images = images.to(DEVICE)
            masks = masks.to(DEVICE).unsqueeze(1)
            
            outputs = model(images)
            loss = criterion(outputs, masks)
            total_loss += loss.item()
            
            # Metric: IoU
            probs = torch.sigmoid(outputs)
            preds = (probs > 0.5).float()
            
            # Simple IoU calculation
            intersection = (preds * masks).sum()
            union = preds.sum() + masks.sum() - intersection
            iou = (intersection + 1e-6) / (union + 1e-6)
            total_iou += iou.item()
            
    return total_loss / len(loader), total_iou / len(loader)

def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # 1. Load Data Index
    with open(INDEX_FILE, 'r') as f:
        full_index = json.load(f)
        
    # 2. Temporal Split
    # Sort by timestamp just in case
    full_index.sort(key=lambda x: x['timestamp'])
    
    split_idx = int(0.8 * len(full_index))
    train_entries = full_index[:split_idx]
    val_entries = full_index[split_idx:]
    
    print(f"Total Samples: {len(full_index)}")
    print(f"Train: {len(train_entries)} | Val: {len(val_entries)}")
    
    # 3. Datasets & Loaders
    train_ds = MichaungDataset(train_entries, transform=get_transforms('train'))
    val_ds = MichaungDataset(val_entries, transform=get_transforms('valid'))
    
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0) # shuffle=False to respect time initially? No, shuffle TRAIN for batch norm stability.
    # Actually, random shuffle in train is standard.
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=2)
    
    # 4. Model
    # U-Net with MobileNetV2 Encoder
    # In channels = 1 (IRBT)
    model = smp.Unet(
        encoder_name="mobilenet_v2",
        encoder_weights="imagenet",
        in_channels=1,
        classes=1,
    )
    model.to(DEVICE)
    
    # 5. Loss & Optimizer
    # DiceLoss fits well for segmentation
    criterion = smp.losses.DiceLoss(mode='binary')
    optimizer = optim.AdamW(model.parameters(), lr=LR)
    
    # 6. Training Loop
    best_iou = 0.0
    
    print("Starting Training...")
    for epoch in range(EPOCHS):
        print(f"\nEpoch {epoch+1}/{EPOCHS}")
        
        train_loss = train_epoch(model, train_loader, criterion, optimizer, None)
        val_loss, val_iou = validate(model, val_loader, criterion)
        
        print(f"Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Val IoU: {val_iou:.4f}")
        
        # Checkpoint
        if val_iou > best_iou:
            best_iou = val_iou
            torch.save(model.state_dict(), os.path.join(MODEL_DIR, "best_model.pth"))
            print("Saved Best Model!")
            
    # Save final
    torch.save(model.state_dict(), os.path.join(MODEL_DIR, "final_model.pth"))
    print("Training Complete.")

if __name__ == "__main__":
    main()
