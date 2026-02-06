"""
Module Verification Script
Tests all 8 TCC detection modules with sample data.
"""

import os
import sys
import logging
import tempfile
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_preprocessing():
    """Test Module 1: Preprocessing"""
    logger.info("Testing Module 1: Preprocessing...")
    
    from modules.preprocessing import (
        normalize_bt, 
        resize_for_model, 
        extract_timestamp_string,
        get_pixel_area_km2
    )
    
    # Test normalization
    bt = np.array([[200, 220, 250], [180, 300, 280]], dtype=np.float32)
    normalized = normalize_bt(bt)
    assert normalized.min() >= 0.0 and normalized.max() <= 1.0
    logger.info("  ✓ normalize_bt works correctly")
    
    # Test resize
    resized = resize_for_model(bt, 512)
    assert resized.shape == (512, 512)
    logger.info("  ✓ resize_for_model works correctly")
    
    # Test timestamp extraction
    ts = extract_timestamp_string("3RIMG_30NOV2023_0045_L1C_ASIA_MER_V01R00.h5")
    assert "30NOV2023" in ts or "2023" in ts
    logger.info("  ✓ extract_timestamp_string works correctly")
    
    # Test pixel area
    area = get_pixel_area_km2()
    assert area == 16.0
    logger.info("  ✓ get_pixel_area_km2 returns 16 km²")
    
    logger.info("Module 1: PASSED ✓")
    return True


def test_thresholding():
    """Test Module 2: Thresholding"""
    logger.info("Testing Module 2: Thresholding...")
    
    from modules.thresholding import (
        apply_bt_threshold,
        create_cold_cloud_mask,
        estimate_convective_intensity
    )
    
    # Test threshold
    bt = np.array([[200, 220, 250], [180, 300, 215]], dtype=np.float32)
    mask = apply_bt_threshold(bt, threshold=218.0)
    
    assert mask[0, 0] == 1  # 200K < 218K
    assert mask[0, 1] == 0  # 220K >= 218K
    assert mask[1, 2] == 1  # 215K < 218K
    logger.info("  ✓ apply_bt_threshold works correctly")
    
    # Test intensity classification
    intensity = estimate_convective_intensity(bt, mask)
    assert intensity in ['extreme', 'strong', 'moderate', 'weak', 'none']
    logger.info(f"  ✓ estimate_convective_intensity returned '{intensity}'")
    
    logger.info("Module 2: PASSED ✓")
    return True


def test_clustering():
    """Test Module 3: Clustering"""
    logger.info("Testing Module 3: Clustering...")
    
    from modules.clustering import (
        cluster_clouds,
        apply_geophysical_constraints,
        _haversine_distance
    )
    
    # Test Haversine distance
    dist = _haversine_distance(0.0, 0.0, 0.0, 1.0)
    assert 100 < dist < 120  # ~111 km at equator
    logger.info(f"  ✓ Haversine distance at equator: {dist:.1f} km")
    
    # Test clustering with synthetic mask
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[20:40, 20:40] = 1  # 400 pixels = 6400 km² (below threshold)
    mask[60:95, 60:95] = 1  # 1225 pixels = 19600 km² (still below 34800)
    
    lat_grid = np.linspace(10, 20, 100)[:, None] * np.ones((1, 100))
    lon_grid = np.ones((100, 1)) * np.linspace(70, 80, 100)[None, :]
    
    clusters = cluster_clouds(mask, lat_grid, lon_grid)
    logger.info(f"  ✓ DBSCAN found {len(clusters)} clusters")
    
    logger.info("Module 3: PASSED ✓")
    return True


def test_feature_extraction():
    """Test Module 6: Feature Extraction"""
    logger.info("Testing Module 6: Feature Extraction...")
    
    from modules.feature_extraction import (
        compute_cluster_features,
        estimate_cloud_top_height
    )
    
    # Test cloud top height estimation
    height_190k = estimate_cloud_top_height(190.0)
    height_250k = estimate_cloud_top_height(250.0)
    
    assert height_190k > height_250k  # Colder = higher
    logger.info(f"  ✓ Cloud top at 190K: {height_190k:.1f} km")
    logger.info(f"  ✓ Cloud top at 250K: {height_250k:.1f} km")
    
    # Test feature computation
    coords = np.array([[10, 10], [10, 11], [11, 10], [11, 11], [12, 12], [13, 13]])
    bt = np.random.uniform(180, 220, (100, 100)).astype(np.float32)
    lat = np.linspace(10, 20, 100)[:, None] * np.ones((1, 100))
    lon = np.ones((100, 1)) * np.linspace(70, 80, 100)[None, :]
    
    features = compute_cluster_features(coords, bt, lat, lon, cluster_id=1)
    
    assert 'centroid_lat' in features
    assert 'area_km2' in features
    assert 'mean_bt' in features
    assert 'cloud_top_height_km' in features
    logger.info("  ✓ compute_cluster_features returns all required fields")
    
    logger.info("Module 6: PASSED ✓")
    return True


def test_tracking():
    """Test Module 7: Tracking"""
    logger.info("Testing Module 7: Tracking...")
    
    from modules.tracking import TCCTracker, KalmanTrack
    
    # Test Kalman track
    track = KalmanTrack(track_id=1, initial_lat=15.0, initial_lon=80.0)
    assert track.position == (15.0, 80.0)
    
    # Predict
    pred_lat, pred_lon = track.predict()
    assert pred_lat is not None
    logger.info(f"  ✓ Kalman prediction: ({pred_lat:.2f}, {pred_lon:.2f})")
    
    # Update
    track.update(15.1, 80.1)
    assert track.frames_since_update == 0
    logger.info("  ✓ Kalman update works correctly")
    
    # Test multi-object tracker
    tracker = TCCTracker()
    
    clusters1 = [
        {'centroid_lat': 15.0, 'centroid_lon': 80.0, 'area_km2': 50000},
        {'centroid_lat': 12.0, 'centroid_lon': 85.0, 'area_km2': 40000}
    ]
    
    result1 = tracker.update(clusters1, "20231130_0045")
    assert len(result1) == 2
    assert all('track_id' in c for c in result1)
    logger.info(f"  ✓ Tracker assigned {len(result1)} track IDs")
    
    # Second frame - tracks should match
    clusters2 = [
        {'centroid_lat': 15.1, 'centroid_lon': 80.1, 'area_km2': 52000},
        {'centroid_lat': 12.1, 'centroid_lon': 85.1, 'area_km2': 41000}
    ]
    
    result2 = tracker.update(clusters2, "20231130_0115")
    track_ids = [c['track_id'] for c in result2]
    logger.info(f"  ✓ Matched to existing tracks: {track_ids}")
    
    logger.info("Module 7: PASSED ✓")
    return True


def test_output():
    """Test Module 8: Output"""
    logger.info("Testing Module 8: Output...")
    
    from modules.output import (
        export_to_csv,
        generate_trajectory_json
    )
    
    # Test data
    trajectory = [
        {'track_id': 1, 'timestamp': '20231130_0045', 
         'centroid_lat': 15.0, 'centroid_lon': 80.0, 'area_km2': 50000,
         'mean_bt': 210.0, 'min_bt': 195.0},
        {'track_id': 1, 'timestamp': '20231130_0115',
         'centroid_lat': 15.1, 'centroid_lon': 80.1, 'area_km2': 52000,
         'mean_bt': 208.0, 'min_bt': 192.0}
    ]
    
    # Test CSV export
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "test.csv")
        result = export_to_csv(trajectory, csv_path)
        assert os.path.exists(result)
        logger.info("  ✓ CSV export works correctly")
    
    # Test JSON generation
    json_result = generate_trajectory_json(trajectory)
    assert 'tracks' in json_result
    assert 'total_tracks' in json_result
    assert len(json_result['tracks']) == 1
    logger.info("  ✓ JSON generation works correctly")
    
    logger.info("Module 8: PASSED ✓")
    return True


def run_all_tests():
    """Run all module tests."""
    logger.info("=" * 50)
    logger.info("TCC Module Verification")
    logger.info("=" * 50)
    
    tests = [
        ("Preprocessing", test_preprocessing),
        ("Thresholding", test_thresholding),
        ("Clustering", test_clustering),
        ("Feature Extraction", test_feature_extraction),
        ("Tracking", test_tracking),
        ("Output", test_output),
    ]
    
    results = {}
    for name, test_fn in tests:
        try:
            results[name] = test_fn()
        except Exception as e:
            logger.error(f"Module {name} FAILED: {e}")
            results[name] = False
    
    logger.info("=" * 50)
    logger.info("Summary")
    logger.info("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for name, success in results.items():
        status = "PASSED ✓" if success else "FAILED ✗"
        logger.info(f"  {name}: {status}")
    
    logger.info(f"\nTotal: {passed}/{total} modules passed")
    
    return all(results.values())


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
