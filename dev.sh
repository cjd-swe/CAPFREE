#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# First-time setup: create .env from example if it doesn't exist
if [ ! -f backend/.env ]; then
  if [ -f backend/.env.example ]; then
    cp backend/.env.example backend/.env
    echo "Created backend/.env from .env.example — set DATABASE_URL before continuing"
    exit 1
  fi
fi

# First-time setup: create venv and install deps if missing
if [ ! -f venv/bin/activate ]; then
  echo "Creating virtualenv..."
  python3 -m venv venv
  source venv/bin/activate
  pip install -r backend/requirements.txt -q
else
  source venv/bin/activate
fi

# Run migrations
(cd backend && alembic upgrade head)

# Kill both servers on Ctrl+C
cleanup() {
  echo ""
  echo "Stopping..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  exit 0
}
trap cleanup INT TERM

# Start backend in background
(cd backend && uvicorn app.main:app --reload --port 8000) &
BACKEND_PID=$!

# Start frontend in background
(cd frontend && npm run dev) &
FRONTEND_PID=$!

echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Press Ctrl+C to stop both."

wait "$BACKEND_PID" "$FRONTEND_PID"
