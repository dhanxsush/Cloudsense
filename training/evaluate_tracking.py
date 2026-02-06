
import pandas as pd
import numpy as np

def calculate_metrics(df, x_col, y_col, label):
    # Calculate step distances (velocity per frame)
    dx = df[x_col].diff()
    dy = df[y_col].diff()
    dist = np.sqrt(dx**2 + dy**2)
    
    # Metrics
    total_dist = dist.sum()
    avg_step = dist.mean()
    max_step = dist.max()
    std_step = dist.std() # Smoothness metric (Lower is better/more consistent)
    
    print(f"\n--- {label} ---")
    print(f"Total Path Length: {total_dist:.2f} px")
    print(f"Avg Step Size:     {avg_step:.2f} px/frame")
    print(f"Max Step (Jump):   {max_step:.2f} px")
    print(f"Volatility (Std):  {std_step:.2f}")
    
    return dist

def main():
    raw_df = pd.read_csv("trajectory_data.csv")
    kalman_df = pd.read_csv("trajectory_kalman.csv")
    
    # 1. Raw Metrics (Raw cx, cy)
    raw_dist = calculate_metrics(raw_df, 'cx', 'cy', "Raw Tracking")
    
    # 2. Kalman Metrics (Smooth cx, cy)
    kalman_dist = calculate_metrics(kalman_df, 'smooth_cx', 'smooth_cy', "Kalman Filtered")
    
    # 3. Improvement Stats
    # Count outliers (where Kalman rejected observation)
    # in kalman_df, 'is_predicted' is True where measurement was rejected OR missing
    outliers = kalman_df['is_predicted'].sum()
    total = len(kalman_df)
    
    print(f"\n--- Refinement Stats ---")
    print(f"Outliers Rejected: {outliers} / {total} frames ({outliers/total*100:.1f}%)")
    print(f"Jump Reduction:    {(raw_dist.max() - kalman_dist.max()):.2f} px reduction in max jump")
    print(f"Smoothness Gain:   Raw Std {raw_dist.std():.2f} -> Kalman Std {kalman_dist.std():.2f}")

if __name__ == "__main__":
    main()
