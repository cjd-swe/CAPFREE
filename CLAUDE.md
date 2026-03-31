# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CAPFREE (SharpWatch) is a full-stack sports picks tracking and analytics platform. It ingests picks from screenshots via OCR or Telegram, auto-grades them using the ESPN unofficial API, and surfaces analytics via a Next.js dashboard.

## Commands

### Backend
```bash
cd backend
source venv/bin/activate          # activate virtualenv
uvicorn app.main:app --reload --port 8000  # dev server

# Tests
python -m pytest tests/ -q        # run all 75 tests
python -m pytest tests/test_parser.py -q  # single test file
python -m pytest tests/ -k "test_name" -q  # single test by name

# Migrations
alembic upgrade head
alembic revision --autogenerate -m "description"
```

### Frontend
```bash
cd frontend
npm install
npm run dev     # http://localhost:3000
npm run build
npm run lint    # ESLint v9
```

## Architecture

### Data Flow

1. **Ingest:** Images arrive via `/api/upload` (HTTP) or Telegram bot (polling). Both paths go through the OCR pipeline (`backend/app/ocr/`).
2. **Parse:** `ocr/pipeline.py` (Tesseract) extracts raw text → `ocr/parser.py` applies 8 regex pattern matchers to produce structured pick data. `ocr/teams.py` maps 250+ team names to sport/league.
3. **Grade:** `routers/picks.py` exposes `/api/picks/{id}/auto-grade` which calls `services/espn_service.py`. That service queries ESPN's unofficial scoreboard API, groups picks by (league, date) to minimize requests, and determines WIN/LOSS/PUSH with profit calculation.
4. **Notify:** New picks from Telegram create entries in the `notifications` table, surfaced via the sidebar bell (polls every 30s).
5. **Analytics:** `routers/analytics.py` computes stats on-the-fly from the SQLite database.

### Backend Structure (`backend/app/`)

- `main.py` — FastAPI app, CORS (allows `localhost:3000`), mounts 6 routers under `/api`, starts Telegram polling on startup
- `database.py` — async SQLAlchemy engine (aiosqlite), session factory
- `config.py` — Pydantic Settings loading from `.env` (e.g., `TELEGRAM_BOT_TOKEN`)
- `models.py` — 4 ORM tables: `cappers`, `picks`, `notifications`, `telegram_queue`
- `schemas.py` — Pydantic request/response schemas
- `ocr/parser.py` — core parsing logic; 459 lines with context tracking for sport/units headers across multi-pick screenshots
- `services/espn_service.py` — ESPN grading; `grade_source` values are `"espn_api"`, `"manual"`, `"auto_win"` (props/unsupported leagues after 24h), or `null` (pending)

### Frontend Structure (`frontend/app/`)

All pages live under `app/dashboard/`. The frontend hardcodes `http://localhost:8000` as the API base URL. The sidebar (`components/ui/sidebar.tsx`) manages navigation and the notification badge.

### Database Schema

| Table | Key Columns |
|---|---|
| `cappers` | id, name (unique), telegram_chat_id |
| `picks` | id, capper_id (FK), date, sport, league, match_key, pick_text, units_risked, odds, result (PENDING/WIN/LOSS/PUSH), profit, grade_source, graded_at |
| `notifications` | id, pick_id (FK cascade), message, read |
| `telegram_queue` | id, message_id, chat_id, photo_path, processed |

### Tech Stack

- **Backend:** FastAPI, async SQLAlchemy + aiosqlite, Alembic, pytesseract + OpenCV, httpx (ESPN), python-telegram-bot (polling)
- **Frontend:** Next.js 16 (App Router), React 19, TypeScript 5, Tailwind CSS 3.4, Recharts

## Known Limitations

- Frontend API URL is hardcoded to `http://localhost:8000` (no env var)
- Uploaded images are not persisted to disk (path stored but file not saved)
- OCR preprocessing (grayscale/threshold) is commented out in `ocr/pipeline.py`
- No authentication on any routes
