# CloudSense - Quick Start Guide

## Running the Complete System

The system now uses a **4-layer microservices architecture**. You need to run all services.

### Option 1: Automated Startup (Recommended)

```bash
./start-services.sh
```

This will start:
- Analysis Service (8001)
- Reporting Service (8002)

**Note:** Backend (8000) and Frontend (5173) are already running.

### Option 2: Manual Startup

Open **2 new terminal windows**:

#### Terminal 1: Analysis Service
```bash
cd analysis-service
python main.py
```

#### Terminal 2: Reporting Service
```bash
cd reporting-service
python main.py
```

### Verify Services

Check all services are running:

```bash
# Backend
curl http://localhost:8000/health

# Analysis
curl http://localhost:8001/health

# Reporting
curl http://localhost:8002/health
```

### Service Ports

- **Frontend:** http://localhost:5173 (already running)
- **Backend:** http://localhost:8000 (already running)
- **Analysis:** http://localhost:8001 (needs to start)
- **Reporting:** http://localhost:8002 (needs to start)

---

## Architecture

```
Frontend (5173)
    ↓
Backend (8000) - API Gateway
    ├→ Analysis (8001) - TCC Detection
    └→ Reporting (8002) - NetCDF Export
```

---

## Troubleshooting

**Error: "Connection refused"**
- Analysis service (8001) is not running
- Start it with: `cd analysis-service && python main.py`

**Error: "Port already in use"**
- Kill existing process: `lsof -ti:8001 | xargs kill -9`
- Then restart the service

---

## Next Steps

Once all services are running:
1. Go to http://localhost:5173
2. Upload a .h5 file
3. System will automatically process and display results
