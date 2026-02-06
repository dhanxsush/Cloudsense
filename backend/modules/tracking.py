"""
Module 7: Temporal Tracking
Kalman filter-based multi-object tracking for TCC trajectory analysis.
"""

import numpy as np
import cv2
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from scipy.optimize import linear_sum_assignment
import logging

logger = logging.getLogger(__name__)

# Tracking parameters
MAX_TRACK_DISTANCE_KM = 200.0  # Maximum movement between frames
TRACK_LOST_THRESHOLD = 3       # Frames before track is deleted
EARTH_RADIUS_KM = 6371.0

# Kalman filter parameters
PROCESS_NOISE_COV = 0.03
MEASUREMENT_NOISE_COV = 1.0


@dataclass
class KalmanTrack:
    """
    Individual track for a TCC cluster with Kalman filter smoothing.
    
    State vector: [lat, lon, velocity_lat, velocity_lon]
    Measurement: [lat, lon]
    """
    track_id: int
    initial_lat: float
    initial_lon: float
    
    # Kalman filter (initialized in __post_init__)
    kf: cv2.KalmanFilter = field(init=False)
    
    # Track state
    frames_since_update: int = 0
    total_observations: int = 1
    
    # History for trajectory analysis
    history: List[Dict] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize Kalman filter."""
        # 4 state variables, 2 measurements
        self.kf = cv2.KalmanFilter(4, 2)
        
        # Transition matrix: [lat, lon, v_lat, v_lon] -> next state
        # Assumes constant velocity model
        self.kf.transitionMatrix = np.array([
            [1, 0, 1, 0],  # lat = lat + v_lat
            [0, 1, 0, 1],  # lon = lon + v_lon
            [0, 0, 1, 0],  # v_lat = v_lat
            [0, 0, 0, 1],  # v_lon = v_lon
        ], dtype=np.float32)
        
        # Measurement matrix: observe [lat, lon]
        self.kf.measurementMatrix = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
        ], dtype=np.float32)
        
        # Process noise
        self.kf.processNoiseCov = np.eye(4, dtype=np.float32) * PROCESS_NOISE_COV
        
        # Measurement noise
        self.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * MEASUREMENT_NOISE_COV
        
        # Initialize state
        self.kf.statePost = np.array([
            [self.initial_lat],
            [self.initial_lon],
            [0],  # Initial velocity = 0
            [0],
        ], dtype=np.float32)
        
        # Add initial position to history
        self.history.append({
            'lat': self.initial_lat,
            'lon': self.initial_lon,
            'is_predicted': False
        })
    
    @property
    def position(self) -> Tuple[float, float]:
        """Get current estimated position (lat, lon)."""
        state = self.kf.statePost
        return float(state[0, 0]), float(state[1, 0])
    
    @property
    def velocity(self) -> Tuple[float, float]:
        """Get current estimated velocity (v_lat, v_lon)."""
        state = self.kf.statePost
        return float(state[2, 0]), float(state[3, 0])
    
    def predict(self) -> Tuple[float, float]:
        """
        Predict next position using Kalman filter.
        
        Returns:
            Predicted (lat, lon) position
        """
        prediction = self.kf.predict()
        self.frames_since_update += 1
        return float(prediction[0, 0]), float(prediction[1, 0])
    
    def update(self, lat: float, lon: float, cluster_data: Optional[Dict] = None):
        """
        Update track with new observation.
        
        Args:
            lat: Observed latitude
            lon: Observed longitude
            cluster_data: Optional cluster features to store in history
        """
        measurement = np.array([[lat], [lon]], dtype=np.float32)
        self.kf.correct(measurement)
        
        self.frames_since_update = 0
        self.total_observations += 1
        
        # Store in history
        entry = {
            'lat': lat,
            'lon': lon,
            'is_predicted': False
        }
        if cluster_data:
            entry.update(cluster_data)
        self.history.append(entry)
    
    def is_active(self) -> bool:
        """Check if track is still active (not lost)."""
        return self.frames_since_update <= TRACK_LOST_THRESHOLD
    
    def get_trajectory(self) -> List[Dict]:
        """Get full trajectory history."""
        return self.history.copy()
    
    def predict_future(self, steps: int = 6, time_interval_hours: float = 0.5) -> List[Dict]:
        """
        Predict future positions based on current velocity.
        
        Uses constant velocity model from Kalman filter to extrapolate
        future TCC positions.
        
        Args:
            steps: Number of future time steps to predict
            time_interval_hours: Time between predictions (default 30 min)
            
        Returns:
            List of predicted positions with timestamps
        """
        predictions = []
        lat, lon = self.position
        v_lat, v_lon = self.velocity
        
        # Calculate average speed in km/h
        speed_kmh = np.sqrt(v_lat**2 + v_lon**2) * 111.0  # deg to km (approx)
        
        # Calculate movement direction (degrees from north)
        direction = np.degrees(np.arctan2(v_lon, v_lat)) % 360
        
        for step in range(1, steps + 1):
            # Predict position at this time step
            pred_lat = lat + v_lat * step
            pred_lon = lon + v_lon * step
            
            # Hours from now
            hours_ahead = step * time_interval_hours
            
            predictions.append({
                'step': step,
                'hours_ahead': hours_ahead,
                'predicted_lat': float(pred_lat),
                'predicted_lon': float(pred_lon),
                'estimated_speed_kmh': float(speed_kmh),
                'movement_direction_deg': float(direction),
                'confidence': max(0.3, 1.0 - (step * 0.1))  # Confidence decreases with time
            })
        
        return predictions


class TCCTracker:
    """
    Multi-object tracker for Tropical Cloud Clusters.
    
    Uses Hungarian algorithm for optimal cluster-to-track assignment
    with Kalman filter smoothing for each track.
    """
    
    def __init__(self, max_distance_km: float = MAX_TRACK_DISTANCE_KM):
        """
        Initialize tracker.
        
        Args:
            max_distance_km: Maximum distance for cluster-track matching
        """
        self.tracks: Dict[int, KalmanTrack] = {}
        self.next_track_id = 1
        self.frame_count = 0
        self.max_distance = max_distance_km
        
    def update(self, clusters: List[Dict], timestamp: str) -> List[Dict]:
        """
        Update tracks with new cluster detections.
        
        Args:
            clusters: List of cluster dictionaries with centroid_lat, centroid_lon
            timestamp: Current frame timestamp
            
        Returns:
            List of tracked clusters with track_id and trajectory info
        """
        self.frame_count += 1
        
        # Predict all existing tracks
        for track in self.tracks.values():
            track.predict()
        
        if not clusters:
            self._cleanup_lost_tracks()
            return []
        
        # Match clusters to tracks
        assignments = self._assign_clusters_to_tracks(clusters)
        
        tracked_output = []
        
        # Update matched tracks
        for cluster_idx, track_id in assignments.items():
            cluster = clusters[cluster_idx]
            track = self.tracks[track_id]
            
            track.update(
                cluster['centroid_lat'],
                cluster['centroid_lon'],
                cluster
            )
            
            # Add tracking info to cluster
            cluster['track_id'] = track_id
            cluster['timestamp'] = timestamp
            cluster['is_predicted'] = False
            cluster['track_length'] = track.total_observations
            tracked_output.append(cluster)
        
        # Create new tracks for unmatched clusters
        unmatched = set(range(len(clusters))) - set(assignments.keys())
        for idx in unmatched:
            cluster = clusters[idx]
            track_id = self._create_track(
                cluster['centroid_lat'],
                cluster['centroid_lon']
            )
            
            cluster['track_id'] = track_id
            cluster['timestamp'] = timestamp
            cluster['is_predicted'] = False
            cluster['track_length'] = 1
            tracked_output.append(cluster)
        
        # Cleanup lost tracks
        self._cleanup_lost_tracks()
        
        logger.debug(f"Frame {self.frame_count}: {len(tracked_output)} tracked clusters, {len(self.tracks)} active tracks")
        
        return tracked_output
    
    def _assign_clusters_to_tracks(self, clusters: List[Dict]) -> Dict[int, int]:
        """
        Match clusters to tracks using Hungarian algorithm.
        
        Returns:
            Dictionary mapping cluster_idx -> track_id
        """
        if not self.tracks or not clusters:
            return {}
        
        track_ids = list(self.tracks.keys())
        n_clusters = len(clusters)
        n_tracks = len(track_ids)
        
        # Build cost matrix (distance in km)
        cost_matrix = np.zeros((n_clusters, n_tracks))
        
        for i, cluster in enumerate(clusters):
            cluster_pos = (cluster['centroid_lat'], cluster['centroid_lon'])
            
            for j, track_id in enumerate(track_ids):
                track = self.tracks[track_id]
                track_pos = track.position
                
                distance = self._haversine_distance(
                    cluster_pos[0], cluster_pos[1],
                    track_pos[0], track_pos[1]
                )
                cost_matrix[i, j] = distance
        
        # Hungarian algorithm
        row_indices, col_indices = linear_sum_assignment(cost_matrix)
        
        # Filter by distance threshold
        assignments = {}
        for i, j in zip(row_indices, col_indices):
            if cost_matrix[i, j] < self.max_distance:
                assignments[i] = track_ids[j]
        
        return assignments
    
    def _create_track(self, lat: float, lon: float) -> int:
        """Create new track and return its ID."""
        track_id = self.next_track_id
        self.next_track_id += 1
        
        self.tracks[track_id] = KalmanTrack(
            track_id=track_id,
            initial_lat=lat,
            initial_lon=lon
        )
        
        logger.debug(f"Created new track {track_id} at ({lat:.2f}, {lon:.2f})")
        return track_id
    
    def _cleanup_lost_tracks(self):
        """Remove tracks that haven't been updated recently."""
        lost_ids = [
            track_id for track_id, track in self.tracks.items()
            if not track.is_active()
        ]
        
        for track_id in lost_ids:
            logger.debug(f"Removed lost track {track_id}")
            del self.tracks[track_id]
    
    def _haversine_distance(self, lat1: float, lon1: float,
                            lat2: float, lon2: float) -> float:
        """Calculate great-circle distance in km."""
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        
        a = np.sin(dlat / 2) ** 2 + \
            np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        
        return EARTH_RADIUS_KM * c
    
    def get_all_trajectories(self) -> Dict[int, List[Dict]]:
        """Get trajectories for all active tracks."""
        return {
            track_id: track.get_trajectory()
            for track_id, track in self.tracks.items()
        }
    
    def get_track(self, track_id: int) -> Optional[KalmanTrack]:
        """Get a specific track by ID."""
        return self.tracks.get(track_id)
    
    def get_all_predictions(self, steps: int = 6) -> Dict[int, List[Dict]]:
        """
        Get future predictions for all active tracks.
        
        Args:
            steps: Number of future time steps to predict
            
        Returns:
            Dictionary mapping track_id to list of predictions
        """
        return {
            track_id: track.predict_future(steps=steps)
            for track_id, track in self.tracks.items()
            if track.total_observations >= 2  # Need at least 2 points for velocity
        }
    
    def reset(self):
        """Reset tracker state."""
        self.tracks.clear()
        self.next_track_id = 1
        self.frame_count = 0
