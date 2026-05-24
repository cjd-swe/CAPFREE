#!/usr/bin/env bash
cd "$(dirname "$0")"
REPO="$(pwd)"
SESSION="sharpwatch"
VENV="$REPO/venv"

# First-time setup: create .env from example if it doesn't exist
if [ ! -f backend/.env ]; then
  if [ -f backend/.env.example ]; then
    cp backend/.env.example backend/.env
    echo "Created backend/.env from .env.example — set DATABASE_URL before continuing"
    exit 1
  fi
fi

# First-time setup: create venv and install deps if missing
if [ ! -f "$VENV/bin/activate" ]; then
  echo "Creating virtualenv..."
  python3 -m venv "$VENV"
  source "$VENV/bin/activate"
  pip install -r backend/requirements.txt -q
fi

# Attach to existing session if already running
if tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux attach-session -t "$SESSION"
  exit 0
fi

ACTIVATE="source '$VENV/bin/activate'"

tmux new-session -d -s "$SESSION" -x "$(tput cols)" -y "$(tput lines)"

# Left pane: migrate then serve (migration output visible; pane stays open on failure)
tmux send-keys -t "$SESSION:0.0" \
  "$ACTIVATE && cd '$REPO/backend' && alembic upgrade head && uvicorn app.main:app --reload --port 8000" Enter

# Right pane: frontend
tmux split-window -h -t "$SESSION"
tmux send-keys -t "$SESSION:0.1" "cd '$REPO/frontend' && npm run dev" Enter

tmux select-pane -t "$SESSION:0.0"
tmux attach-session -t "$SESSION"
