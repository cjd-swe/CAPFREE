# CAPFREE (SharpWatch)

A sports picks tracking and analytics platform. Upload screenshots of picks from cappers (sports betting handicappers), extract them via OCR, grade results, and track accuracy over time to determine which cappers are worth following.

---

## What It Does

1. **Ingest** — Upload images of picks (from Telegram screenshots or other sources); OCR extracts the picks automatically
2. **Track** — Store each pick with capper attribution, sport, odds, and units risked
3. **Grade** — Mark picks WIN / LOSS / PUSH after games resolve; profit is calculated automatically from American odds
4. **Analyze** — Dashboard shows per-capper win rate, ROI, profit over time, and sport breakdowns so you know who to trust

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.8 · FastAPI · SQLAlchemy (async) · SQLite |
| OCR | Tesseract (pytesseract) · OpenCV · Pillow |
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
│   │   ├── main.py              # FastAPI app init, CORS, router mounting
│   │   ├── database.py          # Async SQLAlchemy engine + session factory
│   │   ├── models.py            # ORM models: Capper, Pick, TelegramQueue
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── ocr/
│   │   │   ├── pipeline.py      # Image → raw OCR text (Tesseract)
│   │   │   ├── parser.py        # Raw text → structured picks (8 pattern matchers)
│   │   │   └── teams.py         # Team name → sport/league mapping (250+ teams, 6 leagues)
│   │   ├── routers/
│   │   │   ├── picks.py         # Pick CRUD + grading endpoint
│   │   │   ├── upload.py        # Image upload → OCR → parsed picks
│   │   │   ├── analytics.py     # Stats, leaderboards, daily profit, sport breakdown
│   │   │   ├── settings.py      # Capper CRUD
│   │   │   └── telegram.py      # Telegram webhook (skeleton)
│   │   └── services/
│   │       └── telegram_bot.py  # Telegram bot (skeleton)
│   ├── tests/
│   │   ├── test_parser.py       # 37 parser tests covering all pick formats
│   │   ├── test_teams.py        # 14 team detection tests
│   │   └── test_pipeline.py     # 7 OCR pipeline + end-to-end tests
│   ├── alembic/                 # DB migration history
│   ├── alembic.ini
│   ├── requirements.txt
│   └── sharpwatch.db            # SQLite database file
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Redirects / → /dashboard
│   │   ├── layout.tsx           # Root layout (title: "CAPFREE - Sports Picks Tracker")
│   │   └── dashboard/
│   │       ├── layout.tsx       # Sidebar layout wrapper
│   │       ├── page.tsx         # Main dashboard (stats + recent picks)
│   │       ├── picks/page.tsx   # All picks — filter, grade, delete
│   │       ├── upload/page.tsx  # Upload images or manual entry
│   │       ├── analytics/page.tsx  # Charts (daily profit, win rate by sport)
│   │       ├── cappers/
│   │       │   ├── page.tsx     # Capper leaderboard (cards)
│   │       │   └── [id]/page.tsx  # Individual capper detail
│   │       └── settings/page.tsx  # Capper management (add/edit/delete)
│   └── components/
│       └── ui/sidebar.tsx       # Navigation sidebar
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
| telegram_chat_id | String | Optional, for bot integration |
| created_at | DateTime | |

### `picks`
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | |
| capper_id | FK → cappers | Cascade delete |
| date | Date | Indexed |
| sport | String | NBA / NFL / MLB / NHL / Soccer |
| league | String | Optional sub-league |
| match_key | String | e.g. `"LAL vs BOS"` |
| pick_text | String | e.g. `"Lakers -5.5"` |
| units_risked | Float | Default 1.0 |
| odds | Integer | American odds (e.g. -110, +250) |
| result | Enum | PENDING / WIN / LOSS / PUSH |
| profit | Float | Auto-calculated on grading |
| original_image_path | String | Source image (not yet persisted) |
| raw_text | String | Full OCR output for debugging |

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
| PATCH | `/picks/{id}/grade` | Grade pick → WIN/LOSS/PUSH, calculates profit |

### Upload
| Method | Path | Description |
|---|---|---|
| POST | `/upload/` | Upload images → OCR → return parsed picks (not saved yet) |

### Analytics
| Method | Path | Description |
|---|---|---|
| GET | `/analytics/summary` | Totals: profit, win rate, ROI, active cappers |
| GET | `/analytics/cappers` | Leaderboard sorted by profit |
| GET | `/analytics/capper/{id}` | Detailed stats for one capper |
| GET | `/analytics/daily-profit` | Daily profit for last 30 days |
| GET | `/analytics/sport-performance` | Win rate / ROI / profit by sport |

### Settings
| Method | Path | Description |
|---|---|---|
| GET | `/settings/cappers` | List all cappers |
| POST | `/settings/cappers` | Create capper |
| PATCH | `/settings/cappers/{id}` | Update capper |
| DELETE | `/settings/cappers/{id}` | Delete capper + cascade picks |

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
User assigns capper + reviews/edits picks
    ↓
POST /api/picks for each pick  →  saved to DB
```

**Context headers** — lines like `"NHL: 1 Unit (7:30 PM EST)"`, `"NBA: 1 Unit"`, `"3/11 nba plays"`, or `"Main Card: NCAAB & NBA"` set the active sport, league, and units for all picks that follow on subsequent lines.

**Supported leagues:** NBA · NFL · MLB · NHL · NCAAB · Soccer (MLS/EPL/La Liga) · Tennis (ATP/WTA)

**Profit Calculation (on grading):**
- WIN with negative odds (e.g. -110): `profit = units * (100 / |odds|)`
- WIN with positive odds (e.g. +250): `profit = units * (odds / 100)`
- LOSS: `profit = -units`
- PUSH: `profit = 0`

---

## Running Locally

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

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
python -m pytest tests/ -v
```

63 tests across 3 files covering the parser, team detection, and OCR pipeline.

---

## Known Issues / Incomplete Features

- **Telegram bot** — Model and webhook route exist, but the bot has no message handlers implemented yet
- **Image persistence** — `original_image_path` is stored but images are not saved to disk
- **OCR preprocessing** — Grayscale/threshold preprocessing is commented out in `pipeline.py`; re-enabling it would improve accuracy on noisy images
- **No authentication** — All routes are publicly accessible
- **Hardcoded API URL** — Frontend fetches from `http://localhost:8000` (not environment-variable-driven)
- **No data export** — No CSV/PDF export of picks or stats

---

## Roadmap

- [ ] Implement Telegram bot to auto-ingest photos from group chats
- [ ] Enable OCR preprocessing for better extraction quality on low-contrast images
- [ ] Persist uploaded images to disk with served static paths
- [ ] Environment variable config for API URL
- [ ] Add CSV export for picks and analytics
- [ ] Add authentication (even a simple API key or password gate)
