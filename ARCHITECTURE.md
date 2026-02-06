# CloudSense - System Architecture Documentation

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Component Details](#component-details)
4. [Data Flow](#data-flow)
5. [Technology Stack](#technology-stack)
6. [API Architecture](#api-architecture)
7. [Database Schema](#database-schema)
8. [Deployment Architecture](#deployment-architecture)

---

## 🌐 System Overview

**CloudSense** is an AI-powered tropical cloud intelligence system for real-time detection and tracking of Tropical Cloud Clusters (TCCs) using satellite imagery and deep learning.

**Primary Use Case:** Monitor and track tropical cyclones in the Indian Ocean region using INSAT-3D satellite data.

---

## 🏗️ High-Level Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[React Dashboard<br/>Port 5173]
    end
    
    subgraph "Backend Layer"
        API[FastAPI Server<br/>Port 8000]
        AUTH[Authentication<br/>JWT + bcrypt]
        DB[(SQLite Database<br/>cloudsense.db)]
    end
    
    subgraph "ML Pipeline"
        ENGINE[TCC Analysis Engine]
        MODEL[U-Net Model<br/>PyTorch]
        TRACKER[Kalman Tracker]
    end
    
    subgraph "External Services"
        MOSDAC[MOSDAC API<br/>Satellite Data]
    end
    
    subgraph "Data Storage"
        FILES[File Storage<br/>H5 Files]
        RESULTS[Analysis Results<br/>CSV/JSON]
    end
    
    UI -->|HTTP/REST| API
    API --> AUTH
    API --> DB
    API --> ENGINE
    ENGINE --> MODEL
    ENGINE --> TRACKER
    API --> MOSDAC
    ENGINE --> FILES
    ENGINE --> RESULTS
    
    style UI fill:#3b82f6
    style API fill:#8b5cf6
    style ENGINE fill:#10b981
    style MODEL fill:#f59e0b
    style DB fill:#ef4444
```

---

## 🔧 Component Details

### 1. Frontend (React + Vite)

**Location:** `/frontend/`

**Key Components:**
- **Landing Page** - Marketing/info page
- **Dashboard** - Real-time TCC monitoring with world map
- **Data Upload** - Manual H5 file upload interface
- **Analysis** - Historical analysis viewer
- **Tracking** - Trajectory visualization
- **Insights** - AI-powered analysis
- **Exports** - NetCDF data export
- **Chat** - AI chatbot for queries

**Tech Stack:**
- React 18.3.1
- React Router 6.30.1
- TanStack Query (data fetching)
- Tailwind CSS + shadcn/ui
- Recharts (visualization)

**State Management:**
- React Context API (`AnalysisContext`)
- TanStack Query for server state
- localStorage for auth tokens

---

### 2. Backend (FastAPI)

**Location:** `/backend/`

**Core Files:**
- `app.py` - Main FastAPI application
- `auth.py` - JWT authentication
- `db.py` - SQLite database operations
- `analysis_engine.py` - Basic ML inference
- `tcc_analysis_engine.py` - Advanced TCC detection
- `mosdac_manager.py` - MOSDAC API integration

**Architecture Pattern:** Monolithic with service layer separation

```mermaid
graph LR
    subgraph "FastAPI App"
        ROUTES[API Routes]
        MIDDLEWARE[CORS Middleware]
        LIFESPAN[Lifespan Events]
    end
    
    subgraph "Services"
        AUTH_SVC[Auth Service]
        DB_SVC[Database Service]
        ANALYSIS_SVC[Analysis Service]
        MOSDAC_SVC[MOSDAC Service]
    end
    
    ROUTES --> AUTH_SVC
    ROUTES --> DB_SVC
    ROUTES --> ANALYSIS_SVC
    ROUTES --> MOSDAC_SVC
    
    MIDDLEWARE --> ROUTES
    LIFESPAN --> DB_SVC
```

---

### 3. ML Pipeline

**Location:** `/models/` and `/backend/tcc_analysis_engine.py`

**Components:**

#### a) U-Net Segmentation Model
- **Architecture:** MobileNetV2 encoder + U-Net decoder
- **Input:** 512x512 brightness temperature (BT) images
- **Output:** Binary cloud mask (TCC vs background)
- **Framework:** PyTorch + segmentation-models-pytorch
- **Model File:** `models/models/best_model.pth` (26.7 MB)

#### b) TCC Detection Pipeline
```mermaid
flowchart TD
    A[H5 File Input] --> B[Extract BT Data]
    B --> C[Normalize BT<br/>180-320K]
    C --> D[U-Net Inference]
    D --> E[Binary Mask<br/>Threshold: 0.5]
    E --> F[DBSCAN Clustering]
    F --> G[Compute Metrics<br/>Area, BT, Centroid]
    G --> H[Kalman Tracking]
    H --> I[Output Results]
    
    style D fill:#f59e0b
    style F fill:#10b981
    style H fill:#8b5cf6
```

#### c) Kalman Filter Tracking
- **State Vector:** [lat, lon, velocity_lat, velocity_lon]
- **Measurement:** [lat, lon] from cluster centroids
- **Purpose:** Smooth trajectories, handle missing observations
- **Gating:** Reject outliers >200km from prediction

---

### 4. Database Schema

**Type:** SQLite (single file: `cloudsense.db`)

```mermaid
erDiagram
    users ||--o{ analyses : creates
    analyses ||--o{ analysis_results : contains
    analyses ||--|| analysis_metadata : has
    
    users {
        int id PK
        string username UK
        string email UK
        string password_hash
        datetime created_at
    }
    
    analyses {
        string id PK
        string filename
        datetime upload_timestamp
        string status
        string source
        string file_path
        int user_id FK
    }
    
    analysis_results {
        int id PK
        string analysis_id FK
        string timestamp
        int track_id
        int cluster_id
        float centroid_lat
        float centroid_lon
        float area_km2
        float radius_km
        float mean_bt
        bool is_predicted
    }
    
    analysis_metadata {
        string analysis_id PK
        int total_frames
        float min_bt
        float max_bt
        float mean_bt
        float total_area
    }
```

---

## 🔄 Data Flow

### User Upload Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Engine
    participant DB
    participant Storage
    
    User->>Frontend: Upload H5 file
    Frontend->>API: POST /api/upload
    API->>Storage: Save file
    API->>DB: Create analysis record
    API->>Engine: process_frame()
    Engine->>Engine: U-Net inference
    Engine->>Engine: Cluster detection
    Engine->>Engine: Kalman tracking
    Engine->>DB: Save results
    API->>Frontend: Return analysis_id
    Frontend->>User: Show results
```

### Live Data Pipeline Flow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant MOSDAC
    participant Engine
    participant DB
    
    User->>API: POST /api/pipeline/run
    API->>MOSDAC: Download satellite data
    MOSDAC-->>API: H5 files
    API->>Engine: process_directory()
    loop For each H5 file
        Engine->>Engine: Inference + Tracking
    end
    Engine->>DB: Save live_trajectory.csv
    API-->>User: Pipeline complete
```

---

## 🛠️ Technology Stack

### Frontend
| Category | Technology | Version |
|----------|-----------|---------|
| Framework | React | 18.3.1 |
| Build Tool | Vite | 5.4.19 |
| Routing | React Router | 6.30.1 |
| State | TanStack Query | 5.90.20 |
| Styling | Tailwind CSS | 3.4.17 |
| UI Components | shadcn/ui + Radix UI | Latest |
| Charts | Recharts | 2.15.4 |

### Backend
| Category | Technology | Version |
|----------|-----------|---------|
| Framework | FastAPI | >=0.100.0 |
| Server | Uvicorn | >=0.23.0 |
| Database | SQLite | 3.x |
| Auth | PyJWT + bcrypt | Latest |
| Validation | Pydantic | >=2.0.0 |

### ML/Data Science
| Category | Technology | Version |
|----------|-----------|---------|
| Deep Learning | PyTorch | >=2.0.0 |
| Segmentation | segmentation-models-pytorch | >=0.3.0 |
| Computer Vision | OpenCV | >=4.8.0 |
| Data Processing | NumPy, Pandas | Latest |
| Clustering | scikit-learn (DBSCAN) | >=1.3.0 |
| Tracking | OpenCV Kalman Filter | >=4.8.0 |
| Data Format | h5py (HDF5) | >=3.9.0 |

---

## 📡 API Architecture

### Authentication Endpoints
```
POST   /api/auth/signup       - Register new user
POST   /api/auth/login        - Login with email/password
GET    /api/auth/verify       - Verify JWT token
```

### Analysis Endpoints
```
POST   /api/upload                          - Upload H5 file for analysis
GET    /api/analysis/{id}/status            - Get analysis status
GET    /api/analysis/{id}/trajectory        - Get trajectory data
GET    /api/analysis/{id}/metadata          - Get analysis metadata
GET    /api/analyses/recent?limit=10        - List recent analyses
```

### Data Endpoints
```
GET    /api/analysis/trajectory             - Get Kalman trajectory CSV
GET    /api/analysis/clusters               - Get active cluster stats
POST   /api/pipeline/run                    - Run full MOSDAC pipeline
```

### System Endpoints
```
GET    /health                              - Health check
GET    /static/analysis/{file}              - Serve static files
```

---

## 🗄️ File Structure

```
cloudsense/
├── frontend/                    # React application
│   ├── src/
│   │   ├── components/         # Reusable UI components
│   │   ├── pages/              # Route pages
│   │   ├── contexts/           # React contexts
│   │   ├── hooks/              # Custom hooks
│   │   ├── lib/                # Utilities
│   │   └── services/           # API clients
│   ├── public/                 # Static assets
│   └── package.json
│
├── backend/                     # FastAPI server
│   ├── app.py                  # Main application
│   ├── auth.py                 # Authentication
│   ├── db.py                   # Database operations
│   ├── analysis_engine.py      # Basic ML engine
│   ├── tcc_analysis_engine.py  # Advanced TCC engine
│   ├── mosdac_manager.py       # MOSDAC integration
│   ├── services/               # Service clients
│   ├── routes/                 # Additional routes
│   └── cloudsense.db           # SQLite database
│
├── models/                      # ML models
│   ├── models/
│   │   └── best_model.pth      # Trained U-Net (26.7 MB)
│   ├── inference.py            # Standalone inference
│   └── train.py                # Training script
│
├── training/                    # Training data & scripts
│   ├── data/                   # Historical satellite data
│   └── trajectory_kalman.csv   # Michaung cyclone data
│
├── michaung_analysis/           # Live analysis results
│   └── live_trajectory.csv     # Real-time tracking data
│
└── README.md                    # Documentation
```

---

## 🚀 Deployment Architecture

### Current Setup (Development)

```mermaid
graph TB
    subgraph "Local Machine"
        FE[Frontend<br/>npm run dev<br/>:5173]
        BE[Backend<br/>uvicorn<br/>:8000]
        DB[(SQLite<br/>File)]
        MODEL[Model Files<br/>26.7 MB]
    end
    
    FE -->|HTTP| BE
    BE --> DB
    BE --> MODEL
    
    style FE fill:#3b82f6
    style BE fill:#8b5cf6
    style DB fill:#ef4444
```

### Recommended Production Setup

```mermaid
graph TB
    subgraph "CDN"
        STATIC[Static Assets<br/>React Build]
    end
    
    subgraph "Application Server"
        NGINX[Nginx<br/>Reverse Proxy]
        API1[FastAPI<br/>Instance 1]
        API2[FastAPI<br/>Instance 2]
        API3[FastAPI<br/>Instance 3]
    end
    
    subgraph "Data Layer"
        POSTGRES[(PostgreSQL<br/>Primary DB)]
        REDIS[(Redis<br/>Cache)]
        S3[S3/MinIO<br/>File Storage]
    end
    
    subgraph "ML Layer"
        GPU[GPU Server<br/>Model Inference]
    end
    
    STATIC --> NGINX
    NGINX --> API1
    NGINX --> API2
    NGINX --> API3
    API1 --> POSTGRES
    API2 --> POSTGRES
    API3 --> POSTGRES
    API1 --> REDIS
    API1 --> S3
    API1 --> GPU
    
    style NGINX fill:#10b981
    style POSTGRES fill:#ef4444
    style GPU fill:#f59e0b
```

---

## 🔐 Security Architecture

### Current Implementation
- **Authentication:** JWT tokens (HS256)
- **Password Hashing:** bcrypt
- **CORS:** Configured for localhost
- **Token Storage:** localStorage (frontend)

### Security Concerns (From Code Review)
⚠️ See [`code_review.md`](file:///Users/dhanush/.gemini/antigravity/brain/89c3a8a5-b689-4274-be34-be7edf7db359/code_review.md) for detailed security issues

---

## 📊 Performance Characteristics

### Model Inference
- **Input Size:** 512x512 pixels
- **Inference Time:** ~100-200ms (CPU), ~20-50ms (GPU)
- **Model Size:** 26.7 MB
- **Device:** MPS (Mac) or CPU fallback

### Database
- **Type:** SQLite (single-threaded)
- **Limitation:** Not suitable for high concurrency
- **Recommendation:** Migrate to PostgreSQL for production

### API Response Times
- `/health`: <10ms
- `/api/upload`: 2-5 seconds (includes inference)
- `/api/analysis/clusters`: <100ms
- `/api/pipeline/run`: Minutes (depends on data volume)

---

## 🔄 Data Processing Pipeline

### Brightness Temperature (BT) Processing
```
Raw Counts → LUT Mapping → BT (Kelvin) → Normalization → U-Net Input
```

### TCC Detection Parameters
- **BT Threshold:** 218K (cold cloud tops)
- **Pixel Resolution:** 4km × 4km
- **Minimum TCC Area:** 34,800 km²
- **DBSCAN eps:** 1.5 pixels
- **DBSCAN min_samples:** 5

### Tracking Parameters
- **Max Track Distance:** 200 km
- **Track Lost Threshold:** 3 frames
- **Kalman Process Noise:** 0.03
- **Kalman Measurement Noise:** 1.0

---

## 📈 Scalability Considerations

### Current Limitations
1. SQLite (single-threaded writes)
2. Synchronous DB calls in async endpoints
3. No horizontal scaling
4. No load balancing
5. No caching layer

### Scaling Recommendations
1. **Database:** PostgreSQL with connection pooling
2. **Caching:** Redis for frequently accessed data
3. **File Storage:** S3/MinIO instead of local filesystem
4. **API:** Multiple FastAPI instances behind Nginx
5. **ML:** Separate GPU inference service
6. **Queue:** Celery for async processing

---

## 🎯 Summary

CloudSense is a **monolithic full-stack application** with:
- **Frontend:** React SPA with modern UI
- **Backend:** FastAPI with JWT auth
- **ML:** PyTorch U-Net for cloud segmentation
- **Tracking:** Kalman filter for trajectory smoothing
- **Database:** SQLite for persistence
- **External:** MOSDAC API for satellite data

**Current Status:** Functional for development/research, requires hardening for production use.

**Next Steps:** Address security issues from code review, add tests, improve error handling, and implement production deployment architecture.
