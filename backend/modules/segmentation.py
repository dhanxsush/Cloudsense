"""
Module 5: Deep Learning Segmentation
U-Net with MobileNetV2 encoder for TCC segmentation.
"""

import os
import numpy as np
import torch
import cv2
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Model configuration
IMG_SIZE = 512
DEFAULT_THRESHOLD = 0.5

# Device selection
def get_device() -> torch.device:
    """Get best available device for inference."""
    if torch.cuda.is_available():
        return torch.device('cuda')
    elif torch.backends.mps.is_available():
        return torch.device('mps')
    else:
        return torch.device('cpu')

DEVICE = get_device()
logger.info(f"Using device: {DEVICE}")


def load_unet_model(model_path: str) -> torch.nn.Module:
    """
    Load trained U-Net model with MobileNetV2 encoder.
    
    Args:
        model_path: Path to saved model weights (.pth file)
        
    Returns:
        Loaded PyTorch model in eval mode
        
    Raises:
        FileNotFoundError: If model file doesn't exist
    """
    import segmentation_models_pytorch as smp
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found at: {model_path}")
    
    # Create model architecture
    model = smp.Unet(
        encoder_name="mobilenet_v2",
        encoder_weights=None,  # Load custom weights
        in_channels=1,         # Single-channel BT input
        classes=1,             # Binary segmentation
    )
    
    # Load weights
    state_dict = torch.load(model_path, map_location=DEVICE)
    model.load_state_dict(state_dict)
    
    # Set to evaluation mode
    model.to(DEVICE)
    model.eval()
    
    logger.info(f"Loaded U-Net model from {model_path}")
    return model


def segment(model: torch.nn.Module,
            bt_array: np.ndarray,
            return_probabilities: bool = False) -> np.ndarray:
    """
    Perform U-Net segmentation on brightness temperature image.
    
    Args:
        model: Loaded U-Net model
        bt_array: Brightness temperature array in Kelvin (H, W)
        return_probabilities: If True, return probability map instead of binary mask
        
    Returns:
        Binary mask (uint8) or probability map (float32)
    """
    original_shape = bt_array.shape
    
    # Preprocess
    input_tensor = _preprocess_for_model(bt_array)
    
    # Inference
    with torch.no_grad():
        output = model(input_tensor)
        probabilities = torch.sigmoid(output)
    
    # Convert to numpy
    prob_map = probabilities[0, 0].cpu().numpy()
    
    # Resize back to original dimensions
    prob_map = cv2.resize(prob_map, (original_shape[1], original_shape[0]),
                          interpolation=cv2.INTER_LINEAR)
    
    if return_probabilities:
        return prob_map.astype(np.float32)
    
    # Apply threshold for binary mask
    binary_mask = (prob_map > DEFAULT_THRESHOLD).astype(np.uint8)
    
    return binary_mask


def _preprocess_for_model(bt_array: np.ndarray) -> torch.Tensor:
    """
    Preprocess brightness temperature for model input.
    
    Normalizes to [0, 1] using physics-based bounds and resizes to model dimensions.
    """
    from .preprocessing import normalize_bt, resize_for_model
    
    # Normalize
    normalized = normalize_bt(bt_array)
    
    # Resize
    resized = resize_for_model(normalized, IMG_SIZE)
    
    # Convert to tensor with batch and channel dimensions
    tensor = torch.from_numpy(resized).unsqueeze(0).unsqueeze(0).float()
    
    return tensor.to(DEVICE)


def ensemble_with_threshold(unet_mask: np.ndarray,
                             bt_mask: np.ndarray,
                             mode: str = 'intersection') -> np.ndarray:
    """
    Combine U-Net predictions with physics-based BT threshold mask.
    
    This ensemble approach leverages both:
    - Learned spatial patterns from U-Net
    - Physical constraints from BT threshold
    
    Args:
        unet_mask: Binary mask from U-Net prediction
        bt_mask: Binary mask from BT thresholding
        mode: Combination mode ('intersection', 'union', 'unet_refined')
        
    Returns:
        Combined binary mask
    """
    if mode == 'intersection':
        # Conservative: both methods must agree
        result = (unet_mask & bt_mask).astype(np.uint8)
    elif mode == 'union':
        # Liberal: either method detects cloud
        result = (unet_mask | bt_mask).astype(np.uint8)
    elif mode == 'unet_refined':
        # Use U-Net but only within BT cold regions
        result = (unet_mask * bt_mask).astype(np.uint8)
    else:
        raise ValueError(f"Unknown ensemble mode: {mode}")
    
    return result


def get_prediction_confidence(prob_map: np.ndarray,
                               mask: np.ndarray) -> dict:
    """
    Compute confidence metrics for predictions.
    
    Args:
        prob_map: Probability map from model
        mask: Binary prediction mask
        
    Returns:
        Dictionary with confidence metrics
    """
    if np.sum(mask) == 0:
        return {
            'mean_confidence': 0.0,
            'min_confidence': 0.0,
            'max_confidence': 0.0,
            'high_confidence_fraction': 0.0
        }
    
    positive_probs = prob_map[mask == 1]
    
    return {
        'mean_confidence': float(np.mean(positive_probs)),
        'min_confidence': float(np.min(positive_probs)),
        'max_confidence': float(np.max(positive_probs)),
        'high_confidence_fraction': float(np.mean(positive_probs > 0.8))
    }


class TCCSegmenter:
    """
    High-level segmentation class combining U-Net with BT threshold.
    
    Provides a clean interface for the full segmentation pipeline.
    """
    
    def __init__(self, model_path: str, bt_threshold: float = 218.0):
        """
        Initialize segmenter with model and threshold.
        
        Args:
            model_path: Path to trained U-Net model
            bt_threshold: BT threshold for physics-based masking
        """
        self.model = load_unet_model(model_path)
        self.bt_threshold = bt_threshold
        
    def predict(self, bt_array: np.ndarray,
                ensemble_mode: str = 'intersection') -> Tuple[np.ndarray, np.ndarray]:
        """
        Run full segmentation pipeline.
        
        Args:
            bt_array: Brightness temperature array in Kelvin
            ensemble_mode: How to combine U-Net and BT threshold
            
        Returns:
            Tuple of (final_mask, probability_map)
        """
        from .thresholding import apply_bt_threshold
        
        # U-Net prediction
        prob_map = segment(self.model, bt_array, return_probabilities=True)
        unet_mask = (prob_map > DEFAULT_THRESHOLD).astype(np.uint8)
        
        # Physical threshold
        bt_mask = apply_bt_threshold(bt_array, self.bt_threshold)
        
        # Ensemble
        final_mask = ensemble_with_threshold(unet_mask, bt_mask, mode=ensemble_mode)
        
        return final_mask, prob_map
