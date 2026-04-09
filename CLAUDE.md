# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

CAPFREE (a.k.a. **SharpWatch**) tracks sports handicappers ("cappers"). Screenshots of picks — either uploaded manually or auto-ingested from a Telegram group — are OCR'd, parsed into structured picks, stored as `PENDING`, and later graded against ESPN's unofficial scoreboard API to compute per-capper win rate, ROI, and profit over time.

See `README.md` for the full feature list, API reference, and DB schema. This file is the orientation map; don't duplicate the README here.

## Development commands

**Backend** (Python 3.8, FastAPI, async SQLAlchemy, SQLite). The virtualenv lives at the repo root in `venv/`, not inside `backend/`:

```bash
source venv/bin/activate
cd backend
uvicorn app.main:app --reload --port 8000        # run API on :8000
python -m pytest tests/ -q                       # full test suite (~75 tests)
python -m pytest tests/test_parser.py -q         # single file
python -m pytest tests/test_parser.py::test_name # single test
alembic upgrade head                             # apply migrations (schema is also auto-created on startup via Base.metadata.create_all)
alembic revision --autogenerate -m "msg"         # new migration
```

**Frontend** (Next.js 16 / React 19 / Tailwind 3):

```bash
cd frontend
npm run dev     # http://localhost:3000
npm run build
npm run lint    # eslint (flat config, eslint.config.mjs)
```

There is no combined "start everything" command — backend and frontend run as two processes. The frontend expects the API at `http://localhost:8000` (hardcoded — see "Gotchas" below).

## Architecture

### Request → pick lifecycle

The single most important flow to understand:

```
Image(s)  ─►  routers/upload.py  ─►  ocr/pipeline.py  (Tesseract)
                                  ─►  ocr/parser.py    (raw text → structured picks)
                                  ─►  ocr/teams.py     (team name → league/sport)
          ─►  JSON preview returned to frontend (NOT yet saved)
          ─►  User edits/assigns capper in upload UI
          ─►  POST /api/picks/ for each pick  ─►  DB row, result=PENDING
          ─►  Later: POST /api/picks/auto-grade  ─►  services/espn_service.py
                                                 ─►  result + profit + grade_source set
```

Uploads are a **two-step commit**: `/upload/` returns parsed picks as a preview; nothing is persisted until the frontend POSTs them back via `/api/picks/`. Don't wire upload directly to DB inserts.

### The parser is context-aware (`backend/app/ocr/parser.py`)

This is the trickiest piece of backend logic. Key invariants:

- **Bet-slip fast path first.** `_BET_SLIP_SIGNALS` detects DraftKings/FanDuel/etc. receipts and short-circuits into `_parse_as_bet_slip`, which has completely different parsing rules than capper screenshots. If you add signals or patterns, decide which path they belong to.
- **Sport headers set sticky context.** Lines like `"NHL: 1 Unit (7:30 PM EST)"`, `"3/11 nba plays"`, or `"Main Card: NCAAB & NBA"` set `ctx_sport` / `ctx_league` / `ctx_units` that apply to every subsequent pick line until another header is seen. Picks with no inline sport/units inherit from context.
- **Matchers run in order** inside `_try_parse_line`. There are 8 patterns (sharp-plays, spread-vs-opponent, player-prop, moneyline-units, moneyline-word, over/under, simple-spread, parenthetical, spread-no-units). Order matters — earlier patterns are more specific and win first. When adding a pattern, insert it at the right precedence rather than appending.
- **Deduplication is keyed on `(resolved_full_team_name, numeric_part)`** so OCR variants like `"Boston Univ -128"` and `"Boston University -128"` collapse into one pick. Keep `team_name` set in `_make_pick` for this to work.
- `teams.py` maps ~250 team names to `(league, sport)`. If a team is unknown, the parser falls back to the context sport from the header.

### Grading state machine

`Pick.result` is one of `PENDING / WIN / LOSS / PUSH`. The crucial secondary field is `grade_source`:

| `grade_source` | Meaning                                                                 |
|---|---|
| `espn_api`     | ESPN confirmed                                                          |
| `manual`       | User graded via the picks page                                          |
| `auto_win`     | Fallback — prop, unsupported league, or >24h old with no ESPN match     |
| `null`         | Still pending                                                           |

The leaderboard exposes **Confirmed Win Rate** (espn_api + manual only) vs **Total Win Rate** (includes `auto_win`). Do not conflate them in analytics queries. Profit is always computed from American odds inside the grading code — don't recompute it in routers.

`POST /api/picks/auto-grade` (in `routers/picks.py`) batches PENDING picks by `(league, date)` so one ESPN HTTP call covers N picks from the same day. Preserve that batching when editing.

### Backend layout (`backend/app/`)

- `main.py` — FastAPI app; mounts routers under `/api`; on startup runs `Base.metadata.create_all` **and** kicks off the Telegram polling task (only if `TELEGRAM_BOT_TOKEN` is set and not the placeholder).
- `database.py` — async SQLAlchemy engine + session factory. All DB access is async.
- `models.py` — `Capper`, `Pick`, `Notification`, `TelegramQueue`. Deleting a capper cascades to picks; deleting a pick cascades to notifications.
- `schemas.py` — Pydantic request/response schemas, including `AutoGradeResult`.
- `routers/` — one file per resource (picks, upload, analytics, notifications, settings, telegram). Analytics endpoints compute leaderboards and profit history in SQL, not in Python loops.
- `services/espn_service.py` — ESPN scoreboard fetch + spread/ML/total grading logic. No API key required.
- `services/telegram_bot.py` — python-telegram-bot in **polling mode**. A received photo is OCR'd → parser → picks saved directly as PENDING → a `Notification` row is created.

### Frontend layout (`frontend/app/dashboard/`)

Routing is Next.js App Router. The dashboard layout wraps every page with a sidebar (`components/ui/sidebar.tsx`) that polls `/api/notifications/unread-count` and `/api/picks/` pending count every 30s to render badges. Pages talk directly to `http://localhost:8000/api/...` via `fetch` — there's no shared API client layer. `/` redirects to `/dashboard`.

## Gotchas

- **Virtualenv is at the repo root**, not under `backend/`. Activate with `source venv/bin/activate` from the repo root (or `source ../venv/bin/activate` from `backend/`).
- **CORS allow-list is hardcoded** to `http://localhost:3000` in `main.py`. If you run the frontend on another port, update it there.
- **API URL is hardcoded** to `http://localhost:8000` across frontend pages. There is no env-var indirection yet — grep before changing.
- **Images are not persisted to disk.** `Pick.original_image_path` is a column but nothing writes the file. OCR runs on the in-memory bytes only.
- **OCR preprocessing is commented out** in `ocr/pipeline.py`. Re-enabling grayscale/threshold would improve accuracy but may break parser tests that depend on specific OCR output — re-run the full `tests/` suite if you touch it.
- **No authentication.** All routes are public. Don't assume a `current_user` exists anywhere.
- The Telegram bot skeleton only runs if a real token is in `backend/.env`. Without it, the polling task is silently skipped at startup — a missing bot is not an error.
- `sharpwatch.db` is checked into the repo and contains development data; treat it as disposable but don't `rm` it without checking with the user.
