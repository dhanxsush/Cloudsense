# 2-Backend: API Server

## Overview
FastAPI-based REST API server that orchestrates data ingestion, ML inference, and serves results to the frontend.

**Framework:** FastAPI  
**Database:** SQLite  
**Authentication:** JWT  
**Data Source:** MOSDAC (INSAT-3DR)

---

## Directory Structure
```
2-backend/
├── app.py                 # Main FastAPI application
├── auth.py                # JWT authentication
├── db.py                  # Database operations
├── analysis_engine.py     # ML inference wrapper
├── mosdac_manager.py      # Data download orchestration
├── mosdac_engine/
│   └── mdapi.py          # Official MOSDAC API client
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
└── cloudsense.db         # SQLite database (auto-created)
```

---

## Setup

### 1. Install Dependencies
```bash
cd 2-backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your settings
```

**Required Variables:**
```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///./cloudsense.db
```

### 3. Initialize Database
The database auto-initializes on first run. To manually reset:
```bash
rm cloudsense.db
python -c "from db import init_db; init_db()"
```

---

## Running the Server

### Development
```bash
uvicorn app:app --reload --port 8000
```

### Production
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

**Server will be available at:** http://localhost:8000

---

## API Endpoints

### Authentication
- `POST /api/auth/signup` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/verify` - Verify token validity

### Analysis
- `GET /api/analysis/trajectory` - Get Kalman-smoothed trajectory
- `GET /api/analysis/clusters` - Get latest cluster detections
- `GET /static/analysis/{file}` - Serve analysis images

### Data Pipeline
- `POST /api/upload` - Upload H5 file for manual validation
- `POST /api/pipeline/run` - Trigger live MOSDAC sync + inference

### Health
- `GET /health` - Server health check

---

## API Usage Examples

### 1. Register & Login
```bash
# Signup
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"scientist","email":"user@example.com","password":"secure123"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secure123"}'
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {"id": 1, "username": "scientist", "email": "user@example.com"}
}
```

### 2. Get Trajectory Data
```bash
curl http://localhost:8000/api/analysis/trajectory \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Upload File for Analysis
```bash
curl -X POST http://localhost:8000/api/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@path/to/satellite_image.h5"
```

### 4. Trigger Live Sync
```bash
curl -X POST http://localhost:8000/api/pipeline/run \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "mosdac_user",
    "password": "mosdac_pass",
    "dataset_id": "3RIMG_L1C_ASIA_MER",
    "start_date": "2024-01-26",
    "end_date": "2024-01-26"
  }'
```

---

## Connection to Model

The backend imports the ML model via `analysis_engine.py`:

```python
from analysis_engine import AnalysisEngine

# Initialize (loads model from 1-model/)
engine = AnalysisEngine(model_path="../1-model/models/best_model.pth")

# Process new data
results = engine.process_directory("path/to/h5_files")
# Returns: [{"timestamp": "...", "smooth_cx": 256, "smooth_cy": 128, ...}]
```

**Data Flow:**
1. User uploads H5 file OR triggers MOSDAC sync
2. Backend saves files to disk
3. `AnalysisEngine` runs inference (calls `1-model/`)
4. Results saved to `live_trajectory.csv`
5. Frontend fetches via `/api/analysis/clusters`

---

## Connection to Frontend

Frontend (`3-frontend/`) connects via HTTP:

**Base URL:** `http://localhost:8000`

**Authentication Flow:**
1. User logs in → receives JWT token
2. Token stored in `localStorage`
3. All API calls include: `Authorization: Bearer <token>`

**Example (React/Axios):**
```javascript
const token = localStorage.getItem('token');
const response = await axios.get('http://localhost:8000/api/analysis/clusters', {
  headers: { Authorization: `Bearer ${token}` }
});
```

---

## Troubleshooting

**Port already in use:**
```bash
# Kill existing process
lsof -ti:8000 | xargs kill -9
# Or use different port
uvicorn app:app --port 8001
```

**Model not found:**
```bash
# Ensure path is correct in analysis_engine.py
MODEL_PATH = os.path.join(os.path.dirname(__file__), "../1-model/models/best_model.pth")
```

**CORS errors:**
```python
# Add your frontend URL to app.py (line 31)
allow_origins=["http://localhost:3000", "http://localhost:5173"]
```

**Database locked:**
```bash
# Reset database
rm cloudsense.db
python -c "from db import init_db; init_db()"
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key | (required) |
| `DATABASE_URL` | SQLite path | `sqlite:///./cloudsense.db` |
| `ANALYSIS_DIR` | Path to analysis outputs | `../michaung_analysis` |

---

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black app.py
```

### API Documentation
Auto-generated Swagger docs available at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)
