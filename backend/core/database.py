import sqlite3
import os
from datetime import datetime

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "cloudsense.db")

def get_connection():
    """Get database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn

def init_db():
    """Initialize database with all required tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Users table (existing)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Analyses table (NEW)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            upload_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'processing',
            source TEXT DEFAULT 'manual_upload',
            file_path TEXT,
            user_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Analysis results table (NEW - Extended for TCC metrics)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id TEXT NOT NULL,
            timestamp TEXT,
            track_id INTEGER,
            cluster_id INTEGER,
            smooth_cx REAL,
            smooth_cy REAL,
            centroid_lat REAL,
            centroid_lon REAL,
            area_km2 REAL,
            radius_km REAL,
            min_bt REAL,
            max_bt REAL,
            mean_bt REAL,
            aspect_ratio REAL,
            is_predicted INTEGER DEFAULT 0,
            FOREIGN KEY (analysis_id) REFERENCES analyses(id)
        )
    ''')
    
    # Analysis metadata table (NEW)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_metadata (
            analysis_id TEXT PRIMARY KEY,
            total_frames INTEGER,
            min_bt REAL,
            max_bt REAL,
            mean_bt REAL,
            total_area REAL,
            FOREIGN KEY (analysis_id) REFERENCES analyses(id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Analysis CRUD operations
def create_analysis(analysis_id, filename, file_path, source='manual_upload', user_id=None):
    """Create a new analysis record."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO analyses (id, filename, file_path, source, user_id, status)
        VALUES (?, ?, ?, ?, ?, 'processing')
    ''', (analysis_id, filename, file_path, source, user_id))
    conn.commit()
    conn.close()

def update_analysis_status(analysis_id, status):
    """Update analysis status."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE analyses SET status = ? WHERE id = ?
    ''', (status, analysis_id))
    conn.commit()
    conn.close()

def get_analysis(analysis_id):
    """Get analysis by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM analyses WHERE id = ?', (analysis_id,))
    result = cursor.fetchone()
    conn.close()
    return dict(result) if result else None

def get_recent_analyses(limit=10):
    """Get recent analyses."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM analyses 
        ORDER BY upload_timestamp DESC 
        LIMIT ?
    ''', (limit,))
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def save_analysis_results(analysis_id, results):
    """Save analysis results to database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    for result in results:
        cursor.execute('''
            INSERT INTO analysis_results 
            (analysis_id, timestamp, track_id, cluster_id, 
             smooth_cx, smooth_cy, centroid_lat, centroid_lon,
             area_km2, radius_km, min_bt, max_bt, mean_bt, aspect_ratio, is_predicted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            analysis_id,
            result.get('timestamp'),
            result.get('track_id'),
            result.get('cluster_id'),
            result.get('centroid_x'),  # smooth_cx (pixel space)
            result.get('centroid_y'),  # smooth_cy (pixel space)
            result.get('centroid_lat'),
            result.get('centroid_lon'),
            result.get('area_km2'),
            result.get('radius_km'),
            result.get('min_bt'),
            result.get('max_bt'),
            result.get('mean_bt'),
            result.get('aspect_ratio'),
            1 if result.get('is_predicted') else 0
        ))
    
    conn.commit()
    conn.close()

def get_analysis_results(analysis_id):
    """Get all results for an analysis."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT timestamp, smooth_cx, smooth_cy, is_predicted
        FROM analysis_results
        WHERE analysis_id = ?
        ORDER BY id
    ''', (analysis_id,))
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def save_analysis_metadata(analysis_id, metadata):
    """Save analysis metadata."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO analysis_metadata
        (analysis_id, total_frames, min_bt, max_bt, mean_bt, total_area)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        analysis_id,
        metadata.get('total_frames'),
        metadata.get('min_bt'),
        metadata.get('max_bt'),
        metadata.get('mean_bt'),
        metadata.get('total_area')
    ))
    conn.commit()
    conn.close()

def get_analysis_metadata(analysis_id):
    """Get metadata for an analysis."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM analysis_metadata WHERE analysis_id = ?
    ''', (analysis_id,))
    result = cursor.fetchone()
    conn.close()
    return dict(result) if result else None

# User operations (existing, keeping for compatibility)
def create_user(username, email, password_hash):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        ''', (username, email, password_hash))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None

def get_user_by_email(email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_id(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None
