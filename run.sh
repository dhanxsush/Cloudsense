#!/bin/bash

# CloudSense Launcher
# Usage: ./run.sh

# Function to kill child processes on exit
cleanup() {
    echo ""
    echo "🛑 Stopping CloudSense services..."
    # Kill all child processes in the current process group
    kill 0
    exit
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM EXIT

echo "=================================="
echo "🚀 Starting CloudSense System..."
echo "=================================="

# 1. Start Backend (FastAPI)
echo ""
echo "🔹 Starting Backend on port 8000..."
cd backend

# Check for venv
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "⚠ venv not found in backend/venv. Using system python."
fi

# Run uvicorn in background
uvicorn app:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# 2. Start Frontend (React/Vite)
echo ""
echo "🔹 Starting Frontend on port 5173..."
cd frontend

# Run npm dev in background
npm run dev -- --host &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ CloudSense is running!"
echo "   Backend API: http://localhost:8000/docs"
echo "   Dashboard:   http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop all services."

# Wait for processes
wait $BACKEND_PID $FRONTEND_PID
