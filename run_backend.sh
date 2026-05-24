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

cd backend
alembic upgrade head
exec uvicorn app.main:app --reload --port 8000
