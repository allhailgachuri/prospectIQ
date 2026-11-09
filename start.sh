#!/usr/bin/env bash
# ProspectIQ startup script
# Run from prospectiq_data_engine/ directory in Git Bash

echo ""
echo "============================================"
echo "  ProspectIQ — BuiltByRushion"
echo "  Starting backend + dashboard..."
echo "============================================"
echo ""

# Start FastAPI backend
echo "[1/2] Starting FastAPI backend on http://localhost:8000 ..."
.venv/Scripts/uvicorn api.main:app --reload --port 8000 &
BACKEND_PID=$!

# Give the backend a moment to start
sleep 2

# Start React dashboard
echo "[2/2] Starting React dashboard on http://localhost:6060 ..."
cd dashboard && npm run dev &
FRONTEND_PID=$!

echo ""
echo "============================================"
echo "  Dashboard  : http://localhost:6060"
echo "  API docs   : http://localhost:8000/docs"
echo "  Agency     : https://builtbyrushion.vercel.app/"
echo "============================================"
echo ""
echo "Press Ctrl+C to stop both servers."

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
