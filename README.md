# CAPFREE (SharpWatch)

A sports picks tracking and analytics platform. Upload screenshots of picks from cappers (sports betting handicappers), extract them via OCR, auto-grade results against ESPN live scores, and track accuracy over time to determine which cappers are worth following.

---

## What It Does

1. **Ingest** — Upload screenshots manually or let the Telegram bot auto-ingest photos from a group chat; OCR extracts picks automatically
2. **Track** — Store each pick with capper attribution, sport, odds, units risked, and pick date
3. **Auto-Grade** — One click runs ESPN's API against all pending picks; confirmed results get `grade_source="espn_api"`, unresolvable picks fall back to `"auto_win"` only after 24 hours have passed
4. **Notify** — Telegram-sourced picks create in-app notifications; the sidebar bell badge + Picks nav badge update every 30 seconds
5. **Analyze** — Dashboard shows per-capper confirmed win rate (ESPN/manual only) vs. total win rate (including fallbacks), ROI, profit-over-time chart, and a sortable leaderboard

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.8 · FastAPI · SQLAlchemy (async) · SQLite |
| OCR | Tesseract (pytesseract) · OpenCV · Pillow |
| ESPN Grading | ESPN unofficial scoreboard API (no key required) · httpx |
| Telegram | python-telegram-bot (polling mode for local dev) |
| Migrations | Alembic |
| Frontend | Next.js 16 · React 19 · TypeScript |
| Styling | Tailwind CSS 3.4 |
| Charts | Recharts |
| Icons | Lucide React |

---

## Project Structure

```
CAPFREE/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app init, CORS, router mounting, Telegram startup task
│   │   ├── database.py          # Async SQLAlchemy engine + session factory
│   │   ├── models.py            # ORM models: Capper, Pick, Notification, TelegramQueue
│   │   ├── schemas.py           # Pydantic request/response schemas (incl. AutoGradeResult)
│   │   ├── config.py            # pydantic-settings: TELEGRAM_BOT_TOKEN from .env
│   │   ├── ocr/
│   │   │   ├── pipeline.py      # Image → raw OCR text (Tesseract)
│   │   │   ├── parser.py        # Raw text → structured picks (8 pattern matchers)
│   │   │   └── teams.py         # Team name → sport/league mapping (250+ teams, 6 leagues)
│   │   ├── routers/
│   │   │   ├── picks.py         # Pick CRUD + manual grade + POST /picks/auto-grade
│   │   │   ├── upload.py        # Image upload → OCR → parsed picks
│   │   │   ├── analytics.py     # Stats, leaderboards, daily profit, sport breakdown, profit history
│   │   │   ├── notifications.py # Notification CRUD (unread count, mark read, mark all read)
│   │   │   ├── settings.py      # Capper CRUD
│   │   │   └── telegram.py      # Telegram webhook endpoint
│   │   └── services/
│   │       ├── espn_service.py  # ESPN scoreboard fetch + spread/ML/O-U grading logic
│   │       └── telegram_bot.py  # Telegram bot: photo handler → OCR → picks + notifications
│   ├── tests/
│   │   ├── test_parser.py       # 37 parser tests covering all pick formats
│   │   ├── test_teams.py        # 14 team detection tests
│   │   └── test_pipeline.py     # 7 OCR pipeline + end-to-end tests  (75 total)
│   ├── alembic/                 # DB migration history
│   ├── alembic.ini
│   ├── requirements.txt
│   └── sharpwatch.db            # SQLite database file
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Redirects / → /dashboard
│   │   ├── layout.tsx           # Root layout
│   │   └── dashboard/
│   │       ├── layout.tsx       # Sidebar layout wrapper
│   │       ├── page.tsx         # Dashboard: 5 stat cards + recent activity feed + recent picks
│   │       ├── picks/page.tsx   # All picks — filter, manual grade, auto-grade, grade_source badges
│   │       ├── upload/page.tsx  # Upload images or manual entry; per-row delete; new capper notice
│   │       ├── analytics/page.tsx  # Charts: daily profit, win rate by sport
│   │       ├── cappers/
│   │       │   ├── page.tsx        # Sortable leaderboard table with confirmed/total win rates
│   │       │   └── [id]/page.tsx   # Capper detail: profit-over-time chart + sport breakdown
│   │       └── settings/page.tsx   # Capper management (add/edit/delete)
│   └── components/
│       └── ui/sidebar.tsx       # Navigation: active state, notification bell badge, pending badge
│
└── venv/                        # Python virtualenv
```

---

## Database Schema

### `cappers`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| name | String | Unique, indexed |
| telegram_chat_id | String | Optional |
| created_at | DateTime | |

### `picks`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| capper_id | FK → cappers | |
| date | DateTime | |
| sport | String | NBA / NFL / MLB / NHL / NCAAB / Soccer / etc. |
| league | String | Optional sub-league |
| match_key | String | e.g. `"LAL vs BOS"` |
| pick_text | String | e.g. `"Lakers -5.5"` |
| units_risked | Float | |
| odds | Integer | American odds (e.g. -110, +250) |
| result | String | PENDING / WIN / LOSS / PUSH |
| profit | Float | Auto-calculated on grading |
| grade_source | String | `"manual"` / `"espn_api"` / `"auto_win"` / null |
| graded_at | DateTime | When grading was applied |
| original_image_path | String | Source image path |
| raw_text | String | Full OCR output for debugging |

### `notifications`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| pick_id | FK → picks | CASCADE delete, nullable |
| message | String | e.g. `"New pick from MrBets: Lakers -5.5 (2u)"` |
| read | Boolean | Default false |
| created_at | DateTime | |

### `telegram_queue`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| message_id | String | |
| chat_id | String | |
| photo_path | String | |
| processed | Boolean | |
| created_at | DateTime | |

---

## API Reference

Base URL: `http://localhost:8000/api`

### Picks
| Method | Path | Description |
|---|---|---|
| POST | `/picks/` | Create a pick (auto-creates capper if needed) |
| GET | `/picks/` | List all picks (paginated, newest first) |
| GET | `/picks/{id}` | Get single pick |
| PATCH | `/picks/{id}` | Update pick fields |
| DELETE | `/picks/{id}` | Delete pick |
| GET | `/picks/by-capper/{capper_id}` | Picks for one capper |
| PATCH | `/picks/{id}/grade` | Grade pick → WIN/LOSS/PUSH; sets grade_source="manual" |
| POST | `/picks/auto-grade` | Auto-grade all PENDING picks via ESPN; returns AutoGradeResult |

### Upload
| Method | Path | Description |
|---|---|---|
| POST | `/upload/` | Upload images → OCR → return parsed picks (not saved yet) |

### Analytics
| Method | Path | Description |
|---|---|---|
| GET | `/analytics/summary` | Totals: profit, win rate, ROI, active cappers, pending picks |
| GET | `/analytics/cappers` | Leaderboard with confirmed_win_rate, total_win_rate, pending |
| GET | `/analytics/capper/{id}` | Detailed stats for one capper |
| GET | `/analytics/capper/{id}/profit-history` | Chronological picks with cumulative_profit |
| GET | `/analytics/daily-profit` | Daily profit for last 30 days |
| GET | `/analytics/sport-performance` | Win rate / ROI / profit by sport |

### Notifications
| Method | Path | Description |
|---|---|---|
| GET | `/notifications/` | Last 20 notifications, newest first |
| GET | `/notifications/unread-count` | Returns `{"count": N}` |
| POST | `/notifications/{id}/read` | Mark single notification read |
| POST | `/notifications/read-all` | Mark all notifications read |

### Settings
| Method | Path | Description |
|---|---|---|
| GET | `/settings/cappers` | List all cappers |
| POST | `/settings/cappers` | Create capper |
| PATCH | `/settings/cappers/{id}` | Update capper |
| DELETE | `/settings/cappers/{id}` | Delete capper + cascade picks |

---

## Pick Status Model

```
PENDING   → pick uploaded, game hasn't been graded yet
WIN       → confirmed win
LOSS      → confirmed loss
PUSH      → push / no result
```

`grade_source` distinguishes how a WIN was reached:

| grade_source | Meaning |
|---|---|
| `espn_api` | Verified against ESPN live scores — confirmed result |
| `manual` | Graded by hand via the picks page |
| `auto_win` | Fallback: prop pick, unsupported league, or game not found >24h after pick date |
| null | Not yet graded (PENDING) |

The leaderboard shows **Confirmed Win Rate** (espn_api + manual only) separately from **~Win Rate** (all wins including auto_win fallbacks).

---

## Auto-Grading

Click **"Auto-Grade Pending (N)"** on the Picks page, or call `POST /api/picks/auto-grade`.

The endpoint:
1. Queries all PENDING picks
2. Groups by `(league, date)` — N picks on the same day = 1 ESPN HTTP call
3. For each pick: extracts team → finds game → detects pick type → grades spread / ML / O-U
4. Sets `grade_source="espn_api"` for ESPN-confirmed results
5. Sets `grade_source="auto_win"` for: props, unsupported leagues (Soccer/UFC/Tennis), or games not found in ESPN that are more than 24 hours old
6. Leaves picks PENDING if the game is still in progress or was posted today
7. Returns a summary: `graded_by_api`, `auto_win`, `skipped_not_final`, `errors`

---

## OCR & Parsing Pipeline

```
Upload image(s)
    ↓
pipeline.py  →  Tesseract OCR  →  raw text string
    ↓
parser.py    →  context tracking (sport/units headers)
             →  8 pattern matchers tried in order:
                  1. Spread + opponent:  "Indiana -6.5 (-110) v. Northwestern 10u"
                  2. Player prop:        "Kevin Durant O34.5 PRA -110 1u"
                  3. Moneyline (ML):     "ChiefsML 1.5u"
                  4. Moneyline (word):   "Capitals Moneyline"
                  5. Over/Under:         "Clemson/Wake Forest Under 143"
                  6. Simple spread:      "Lakers -5.5 2u"
                  7. Parenthetical:      "(LAKERS -3.5)"
                  8. Spread no units:    "Nuggets -5 Alternate Line"
    ↓
teams.py     →  team/player name  →  (league, sport)
             →  falls back to context sport if team unknown
    ↓
Returns list of structured picks to frontend
    ↓
User assigns capper, reviews/removes picks, confirms
    ↓
POST /api/picks for each pick  →  saved to DB as PENDING
```

**Context headers** — lines like `"NHL: 1 Unit (7:30 PM EST)"`, `"NBA: 1 Unit"`, `"3/11 nba plays"`, or `"Main Card: NCAAB & NBA"` set the active sport, league, and units for all picks that follow.

**Supported leagues:** NBA · NFL · MLB · NHL · NCAAB · Soccer (MLS/EPL/La Liga) · Tennis (ATP/WTA)

**Profit Calculation (American odds):**
- WIN with negative odds (e.g. -110): `profit = units × (100 / |odds|)`
- WIN with positive odds (e.g. +250): `profit = units × (odds / 100)`
- WIN with no odds: `profit = units` (even money)
- LOSS: `profit = -units`
- PUSH: `profit = 0`

---

## Telegram Bot

Add the bot to a group and it will auto-ingest any photo posted there:

1. Set `TELEGRAM_BOT_TOKEN=your_token` in `backend/.env`
2. Start the backend — polling begins automatically on startup
3. Post a picks screenshot to the monitored group
4. Picks appear in the dashboard as PENDING; the notification bell shows the unread count

The bot runs in **polling mode** (no public URL required for local dev).

---

## Running Locally

### Backend
```bash
cd backend
source venv/bin/activate      # or: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# Optional: configure Telegram
echo "TELEGRAM_BOT_TOKEN=your_token_here" > .env

uvicorn app.main:app --reload --port 8000
```

The SQLite database is created automatically on first startup (SQLAlchemy `create_all`). Alembic migrations are tracked in `alembic/versions/` and can be applied with `alembic upgrade head` if you have Alembic installed.

### Frontend
```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

---

## Running Tests

```bash
cd backend
source ../venv/bin/activate
python -m pytest tests/ -q
```

75 tests across 3 files covering the parser, team detection, and OCR pipeline.

---

## Known Issues / Incomplete Features

- **Image persistence** — `original_image_path` is stored but images are not saved to disk
- **OCR preprocessing** — Grayscale/threshold preprocessing is commented out in `pipeline.py`; re-enabling it would improve accuracy on noisy images
- **No authentication** — All routes are publicly accessible
- **Hardcoded API URL** — Frontend fetches from `http://localhost:8000` (not environment-variable-driven)
- **No data export** — No CSV/PDF export of picks or stats

---

## Roadmap

- [ ] Enable OCR preprocessing for better extraction quality on low-contrast images
- [ ] Persist uploaded images to disk with served static paths
- [ ] Environment variable config for frontend API URL
- [ ] Add CSV export for picks and analytics
- [ ] Add authentication (API key or password gate)
