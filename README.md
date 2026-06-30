# CAPFREE (SharpWatch)

SharpWatch is a private sports-picks tracker for monitoring cappers over time. It ingests picks from screenshots or manual entry, stores them in Postgres, auto-grades supported bets with live-score providers, and exposes a Next.js dashboard for review, analytics, and capper comparisons.

## Live

| | URL |
| --- | --- |
| Frontend | https://capfree-eight.vercel.app |
| Backend API | https://sharpwatch-api.onrender.com |

## Current Status

The repo currently includes:

- A FastAPI backend with cookie-based password auth, OCR/vision-assisted pick parsing, grading, notifications, and analytics APIs
- A Next.js frontend with login, dashboard, picks management, upload/manual entry, analytics, capper detail pages, capper comparison, and settings
- Postgres/Alembic database support
- Optional Telegram ingestion support
- A hybrid parsing flow: Tesseract first, Claude vision fallback when OCR looks unreliable

## Core Workflow

1. Upload screenshots or enter picks manually.
2. Parse picks from OCR, or escalate to Claude vision when OCR confidence is poor.
3. Save picks under a capper, with duplicate detection to avoid re-importing the same pick for the same day.
4. Auto-grade pending picks through supported scoreboard providers.
5. Review results in the dashboard, picks table, analytics views, and capper comparison pages.

## Main Features

- Password-protected app using an HTTP-only JWT cookie
- Screenshot upload with drag/drop and multi-image support
- Manual pick entry
- Auto-detected capper names from screenshots
- Duplicate pick detection on create
- Bulk grade and bulk delete actions for picks
- Inline game date editing on the picks table (pencil icon, saves on change)
- CSV export from the picks page
- Auto-grading with provider fallback
- ESPN closing odds auto-populated during grading when odds are missing
- Backfill odds for already-graded picks via ESPN core API
- Capper notes on individual capper pages
- In-app notifications with unread counts and popup alerts
- Optional Telegram bot polling and webhook endpoint

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | FastAPI, SQLAlchemy async, Alembic, asyncpg |
| Database | PostgreSQL |
| Parsing | Tesseract, OpenCV, Pillow, Claude vision fallback via Anthropic |
| Grading | ESPN + Sofascore provider layer |
| Frontend | Next.js 16, React 19, TypeScript |
| UI | Tailwind CSS, Lucide React, Recharts |

## Project Structure

```text
CAPFREE/
├── backend/
│   ├── app/
│   │   ├── auth.py                  # Password login, JWT cookie auth
│   │   ├── config.py                # Env-driven settings
│   │   ├── database.py              # Async engine/session setup
│   │   ├── main.py                  # FastAPI app + router wiring
│   │   ├── models.py                # Capper, Pick, Notification, TelegramQueue
│   │   ├── schemas.py               # Pydantic schemas
│   │   ├── ocr/
│   │   │   ├── parse_router.py      # OCR-first, vision-fallback router
│   │   │   ├── parser.py            # Regex parser + capper extraction
│   │   │   ├── pipeline.py          # Image preprocessing + OCR
│   │   │   ├── teams.py             # Team/league mapping
│   │   │   └── vision_parser.py     # Claude vision parser
│   │   ├── routers/
│   │   │   ├── analytics.py
│   │   │   ├── notifications.py
│   │   │   ├── picks.py
│   │   │   ├── settings.py
│   │   │   ├── telegram.py
│   │   │   └── upload.py
│   │   └── services/
│   │       ├── grading/             # Provider-based grading orchestration
│   │       └── telegram_bot.py
│   ├── alembic/
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── login/page.tsx
│   │   └── dashboard/
│   │       ├── analytics/page.tsx
│   │       ├── cappers/page.tsx
│   │       ├── cappers/[id]/page.tsx
│   │       ├── cappers/compare/page.tsx
│   │       ├── picks/page.tsx
│   │       ├── settings/page.tsx
│   │       └── upload/page.tsx
│   ├── components/ui/sidebar.tsx
│   ├── lib/api.ts
│   └── .env.example
├── dev.sh
├── dev-tmux.sh
└── run_backend.sh
```

## Setup

### Backend env

Create `backend/.env` from `backend/.env.example`.

Important variables:

- `DATABASE_URL`: required
- `APP_PASSWORD`: optional; if empty, auth is disabled
- `JWT_SECRET`: required when auth is enabled
- `CORS_ORIGINS`: comma-separated frontend origins
- `TELEGRAM_BOT_TOKEN`: optional
- `ANTHROPIC_API_KEY`: required only for vision parsing
- `PARSE_ENGINE`: `hybrid`, `ocr`, or `vision`
- `VISION_MODEL`: Claude model used by the vision parser

### Frontend env

Create `frontend/.env.local` from `frontend/.env.example`.

- `NEXT_PUBLIC_API_URL=http://localhost:8000`

## Running Locally

### One-command dev

```bash
./dev.sh
```

This script:

- creates `backend/.env` from the example if needed
- creates `venv/` if needed
- installs backend dependencies if needed
- runs Alembic migrations
- starts the backend on `:8000`
- starts the frontend on `:3000`

### tmux dev session

```bash
./dev-tmux.sh
```

### Backend only

```bash
./run_backend.sh
```

## Auth Model

- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`

All non-auth API routes are wrapped in `require_auth`. If `APP_PASSWORD` is empty, auth is effectively disabled.

## Parsing Pipeline

Default mode is `PARSE_ENGINE=hybrid`.

1. Tesseract OCR extracts raw text.
2. Regex parsing attempts structured picks and capper extraction.
3. If OCR output looks unreliable, the backend calls the Claude vision parser.
4. If vision still returns no picks, upload returns an empty result for manual review rather than silently saving bad OCR output.

Upload responses include:

- `picks`
- `detected_capper`
- `raw_text`
- `failed_images`

## Auto-Grading

Pending picks are graded through the provider orchestrator in `backend/app/services/grading/`.

Current behavior:

- Supported sources: ESPN and Sofascore
- Supported picks are graded against fetched event data
- Props and unsupported leagues can be marked `auto_win`
- Unmatched older picks can also fall back to `auto_win`
- `grade_source` is set to `espn_api`, `manual`, or `auto_win`
- `game_date` is stored when a provider resolves the event date
- When a pick has no odds, closing line is fetched from the ESPN core API (DraftKings) and stored before profit is calculated
- `POST /picks/backfill-odds` runs the same odds lookup for already-graded picks with null odds

## Current Data Model

### `cappers`

- `id`
- `name`
- `telegram_chat_id`
- `notes`
- `created_at`

### `picks`

- `id`
- `capper_id`
- `date`
- `sport`
- `league`
- `match_key`
- `pick_text`
- `units_risked`
- `odds`
- `result`
- `profit`
- `original_image_path`
- `raw_text`
- `game_date`
- `grade_source`
- `graded_at`

### `notifications`

- `id`
- `pick_id`
- `message`
- `read`
- `created_at`

### `telegram_queue`

- `id`
- `message_id`
- `chat_id`
- `photo_path`
- `processed`
- `created_at`

## API Surface

Base URL: `http://localhost:8000/api`

### Auth

- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/logout`

### Picks

- `POST /picks/`
- `GET /picks/`
- `GET /picks/{id}`
- `PATCH /picks/{id}`
- `DELETE /picks/{id}`
- `GET /picks/by-capper/{capper_id}`
- `PATCH /picks/{id}/grade`
- `POST /picks/auto-grade`
- `POST /picks/bulk-grade`
- `POST /picks/bulk-delete`
- `POST /picks/backfill-odds`

### Upload

- `POST /upload/`

### Analytics

- `GET /analytics/summary`
- `GET /analytics/cappers`
- `GET /analytics/capper/{id}`
- `GET /analytics/capper/{id}/profit-history`
- `GET /analytics/daily-profit`
- `GET /analytics/sport-performance`

### Notifications

- `GET /notifications/`
- `GET /notifications/unread-count`
- `POST /notifications/{id}/read`
- `POST /notifications/read-all`

### Settings

- `GET /settings/cappers`
- `POST /settings/cappers`
- `PATCH /settings/cappers/{id}`
- `DELETE /settings/cappers/{id}`

### Telegram

- `POST /telegram/webhook`

## Frontend Pages

- `/login`: password login
- `/dashboard`: summary stats, top cappers, recent picks, recent notifications
- `/dashboard/picks`: filters, manual grading, auto-grading, bulk actions, CSV export
- `/dashboard/upload`: screenshot upload and manual pick entry
- `/dashboard/analytics`: overall and per-capper charts
- `/dashboard/cappers`: sortable leaderboard
- `/dashboard/cappers/[id]`: capper details, notes, streaks, period stats, pick history
- `/dashboard/cappers/compare`: side-by-side capper comparison
- `/dashboard/settings`: capper CRUD

## Tests

The repo includes backend tests for:

- parser behavior
- OCR pipeline basics
- capper-name extraction
- team/league detection
