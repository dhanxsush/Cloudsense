# CloudSense: AI-Powered Tropical Cloud Intelligence

Real-time detection and tracking of Tropical Cloud Clusters (TCCs) using satellite imagery and deep learning.

---

## 🏗️ Project Structure

```
cloudsense/
├── frontend/          # React dashboard (User Interface)
├── backend/           # FastAPI server (API & Orchestration)
├── models/            # Trained ML models (Inference)
└── training/          # Dataset & training scripts
```

---

## 📦 Modules

### [frontend/](./frontend/) - User Interface
React-based dashboard for real-time monitoring.

**Quick Start:**
```bash
cd frontend
npm install
npm run dev
```
**Access:** http://localhost:5173

---

### [backend/](./backend/) - API Server
FastAPI server that connects everything together.

**Quick Start:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```
**API Docs:** http://localhost:8000/docs

---

### [models/](./models/) - ML Inference
Trained U-Net model for cloud detection.

**Contents:**
- `best_model.pth` - Trained weights
- `inference.py` - Standalone inference script
- `README.md` - Usage documentation

---

### [training/](./training/) - Dataset & Training
Historical Michaung cyclone data and training scripts.

**Contents:**
- `data/raw/` - HDF5 satellite imagery
- `train_model.py` - Training script
- `track_kalman.py` - Trajectory analysis
- Dataset index and labels

**Note:** This folder contains large datasets and is not required for running the application.

---

## 🚀 Quick Start (Full System)

### 1. Start Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

### 2. Start Frontend
Open new terminal:
```bash
cd frontend
npm install
npm run dev
```

### 3. Access Application
- **Dashboard:** http://localhost:5173
- **API:** http://localhost:8000/docs

---

## 🔗 How Modules Connect

```
┌─────────────┐
│  frontend/  │ ──HTTP──▶ ┌──────────┐
│   (React)   │           │ backend/ │
└─────────────┘           │ (FastAPI)│
                          └──────────┘
                               │
                               │ imports
                               ▼
                          ┌──────────┐
                          │ models/  │
                          │ (U-Net)  │
                          └──────────┘
                               │
                               │ trained on
                               ▼
                          ┌──────────┐
                          │training/ │
                          │(Dataset) │
                          └──────────┘
```

**Data Flow:**
1. User uploads file via `frontend/`
2. `backend/` receives file
3. `backend/` calls `models/inference.py`
4. Results sent back to `frontend/`

---

## 📖 Documentation

Each module has detailed README:
- **[frontend/README.md](./frontend/README.md)** - UI components, routing
- **[backend/README.md](./backend/README.md)** - API endpoints, auth
- **[models/README.md](./models/README.md)** - Model architecture, usage
- **[training/README.md](./training/README.md)** - Dataset, training process

---

## 🐛 Troubleshooting

**Backend won't start:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --port 8000
```

**Frontend blank page:**
```bash
cd frontend
rm -rf node_modules
npm install
npm run dev
```

**Model not found:**
```bash
# Verify model exists
ls models/best_model.pth
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push and create Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

**Built for atmospheric science research 🌍**