# ThePulse

Football betting odds aggregator and pick tracker (MVP). Pulls live odds from
[The Odds API](https://the-odds-api.com), lets you compare lines across
sportsbooks, log picks, and track closing line value (CLV), win rate, and ROI.
Includes a simple Elo model for NFL teams to flag potential value against the
market.

**Stack:** FastAPI + SQLAlchemy (SQLite for local dev, Postgres for prod) · React + Vite + TailwindCSS · APScheduler.

## Project structure

```
ThePulse/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, startup odds fetch + scheduler
│   │   ├── config.py          # env-driven settings (pydantic-settings)
│   │   ├── database.py        # SQLAlchemy engine/session + init_db()
│   │   ├── models.py          # Game, OddsSnapshot, Pick, TeamElo
│   │   ├── schemas.py         # Pydantic request/response models
│   │   ├── odds_api.py        # The Odds API client
│   │   ├── ingest.py          # raw odds -> DB rows, closing-line + CLV backfill
│   │   ├── elo.py             # Elo rating math
│   │   ├── probability.py     # American odds / spread <-> implied probability
│   │   ├── scheduler.py       # APScheduler: refresh odds every N hours
│   │   ├── routers/           # odds, lines, picks, stats, elo endpoints
│   │   └── scripts/
│   │       ├── init_db.py                  # create tables ("migration" for MVP)
│   │       ├── load_historical_data.py     # nfl-data-py -> games + closing lines
│   │       ├── load_historical_cfb_data.py # CFBD API -> college games + closing lines
│   │       └── compute_elo.py              # replay history -> Elo ratings + value (NFL only)
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── pages/          # Home, GameDetail, Picks, Dashboard
    │   ├── components/     # GamesTable, OddsComparisonTable, PickForm, PicksList, ClvTrendChart
    │   └── api.js           # axios client for the backend
    └── .env.example
```

## Setup

### 1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env`:
- `ODDS_API_KEY` — get a free key at [the-odds-api.com](https://the-odds-api.com) (500 requests/month free tier).
- `CFBD_API_KEY` — get a free key at [collegefootballdata.com/key](https://collegefootballdata.com/key). Only needed for the college historical data pipeline below, not for the live API server.
- `DATABASE_URL` — defaults to local SQLite (`sqlite:///./thepulse.db`), zero setup. Point it at Postgres for prod (see below).
- `NFL_SEASON_START` / `CFB_SEASON_START` — kickoff of each league's first game; used to derive a week number from each game's date (they're set separately because the college season starts earlier and has a "week 0").

Create the database tables (the "migration" step for this MVP — no Alembic needed, SQLAlchemy creates the schema directly):

```bash
python -m app.scripts.init_db
```

Run the API:

```bash
uvicorn app.main:app --reload --port 8000
```

On startup it fetches current odds once and starts the APScheduler job that
refreshes every `ODDS_REFRESH_INTERVAL_HOURS` (default 2h). Docs at
`http://localhost:8000/docs`.

### 2. Load historical data + Elo (optional, Phase 2 & 4)

Install the data-pipeline extras (kept separate from `requirements.txt` —
see `requirements-data.txt` for why nfl-data-py needs `--no-deps`):

```bash
pip install -r requirements-data.txt
pip install --no-deps nfl-data-py==0.3.3
```

Then, with the venv active:

```bash
python -m app.scripts.load_historical_data --seasons 2024 2025
python -m app.scripts.compute_elo
```

This pulls the last 2 NFL seasons (schedules, final scores, closing Vegas
lines) via [`nfl-data-py`](https://github.com/nflverse/nfl_data_py) — sourced
from nflverse's public data, which mirrors Pro-Football-Reference — and
computes Elo ratings + Elo-vs-market value for upcoming games.

For college football, load the last 2 FBS seasons (schedules, final scores,
closing betting lines) from [CollegeFootballData.com](https://collegefootballdata.com/)
— no extra packages needed, it's called directly over `httpx`:

```bash
python -m app.scripts.load_historical_cfb_data --seasons 2024 2025
```

There's no college Elo — the Elo model is NFL-only.

### 3. Postgres for production

Either use a local Postgres install (`createdb thepulse`), or spin one up with Docker:

```bash
docker compose up -d postgres
```

(This starts Postgres on `localhost:5432` with user/password/db `thepulse` — matches the connection string below.)

Set in `backend/.env`:

```
DATABASE_URL=postgresql://thepulse:thepulse@localhost:5432/thepulse
```

Then re-run `python -m app.scripts.init_db` against the new database.

### 4. Frontend

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_BASE_URL defaults to http://localhost:8000
npm run dev
```

Open `http://localhost:5173`.

## API routes

| Method | Route | Description |
|---|---|---|
| GET | `/odds?week={week}&league={nfl\|college}` | Aggregated latest odds per game |
| GET | `/lines?game={id}` | Spread/moneyline/total for one game, grouped by sportsbook |
| POST | `/picks` | Save a pick with odds captured at entry |
| GET | `/picks` | Saved picks, with CLV backfilled once games kick off |
| PATCH | `/picks/{id}/result` | Set a pick's result (win/loss/push) |
| GET | `/stats/dashboard` | Win rate, ROI, avg CLV, CLV trend |
| GET | `/elo/ratings` | Current Elo ratings by team |
| GET | `/elo/value` | Upcoming games where Elo diverges from the market |
| GET | `/health` | Liveness check |

## Notes / MVP constraints

- No authentication — picks are global, not per-user.
- CLV is computed as the change in implied win probability (in percentage
  points) between your entry price and the last odds snapshot recorded before
  kickoff for that book/market/side.
- Spread-to-probability uses a normal-distribution approximation with a
  13.86-point NFL margin stdev; Elo uses a margin-of-victory-adjusted update
  with a fixed home-field-advantage constant. Both are simple baselines, not
  production-grade models.
- The Odds API's free tier only returns *upcoming* games — historical odds
  come from the `load_historical_data.py` / nfl-data-py (NFL) and
  `load_historical_cfb_data.py` / CFBD API (college) pipelines instead.
- College betting lines from CFBD don't include vig-adjusted spread/total
  prices (only the number, not the odds), so those default to -110; the
  moneylines themselves are real.
