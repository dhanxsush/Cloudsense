# Module 1: Preprocessing - H5 data loading and normalization
# Module 2: Physical Thresholding - Cold cloud isolation

from .preprocessing import (
    load_h5_file,
    normalize_bt,
    resize_for_model,
    extract_timestamp,
)

from .thresholding import (
    apply_bt_threshold,
    create_cold_cloud_mask,
)

from .clustering import (
    cluster_clouds,
    apply_geophysical_constraints,
)

from .pseudo_labels import (
    generate_pseudo_labels,
    save_mask,
)

from .segmentation import (
    load_unet_model,
    segment,
    ensemble_with_threshold,
)

from .feature_extraction import (
    compute_cluster_features,
    estimate_cloud_top_height,
)

from .tracking import (
    TCCTracker,
    KalmanTrack,
)

from .output import (
    export_to_netcdf,
    export_to_csv,
    generate_trajectory_json,
)

from .pipeline import TCCPipeline

__all__ = [
    # Module 1
    'load_h5_file',
    'normalize_bt', 
    'resize_for_model',
    'extract_timestamp',
    # Module 2
    'apply_bt_threshold',
    'create_cold_cloud_mask',
    # Module 3
    'cluster_clouds',
    'apply_geophysical_constraints',
    # Module 4
    'generate_pseudo_labels',
    'save_mask',
    # Module 5
    'load_unet_model',
    'segment',
    'ensemble_with_threshold',
    # Module 6
    'compute_cluster_features',
    'estimate_cloud_top_height',
    # Module 7
    'TCCTracker',
    'KalmanTrack',
    # Module 8
    'export_to_netcdf',
    'export_to_csv',
    'generate_trajectory_json',
    # Pipeline
    'TCCPipeline',
]
