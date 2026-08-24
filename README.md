# ThePulse

Football betting odds aggregator and pick tracker (MVP). Pulls live odds from
[The Odds API](https://the-odds-api.com), lets you compare lines across
sportsbooks, log picks, and track closing line value (CLV), win rate, and ROI.
Includes a simple Elo model for NFL and college (FBS) teams to flag potential
value against the market.

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
│   │   ├── elo.py             # Elo rating math (shared by both leagues)
│   │   ├── teams.py           # Odds API NFL team name -> nflverse abbreviation
│   │   ├── teams_cfb.py       # Odds API CFB team name -> CFBD school name (generated)
│   │   ├── probability.py     # American odds / spread <-> implied probability
│   │   ├── scheduler.py       # APScheduler: refresh odds every N hours
│   │   ├── routers/           # odds, lines, picks, stats, elo endpoints
│   │   └── scripts/
│   │       ├── init_db.py                  # create tables ("migration" for MVP)
│   │       ├── load_historical_data.py     # nfl-data-py -> games + closing lines
│   │       ├── load_historical_cfb_data.py # CFBD API -> college games + closing lines
│   │       ├── generate_cfb_teams.py       # (re)generates teams_cfb.py from CFBD's /teams
│   │       └── compute_elo.py              # replay history -> Elo ratings + value
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── pages/          # Home, GameDetail, Picks, Dashboard, EloValue
    │   ├── components/     # GamesTable, OddsComparisonTable, PickForm, PicksList, ClvTrendChart, LeagueWeekSelector
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
python -m app.scripts.compute_elo --league nfl
```

This pulls the last 2 NFL seasons (schedules, final scores, closing Vegas
lines) via [`nfl-data-py`](https://github.com/nflverse/nfl_data_py) — sourced
from nflverse's public data, which mirrors Pro-Football-Reference — and
computes Elo ratings + Elo-vs-market value for upcoming games.

For college football, load the last 2 FBS seasons (schedules, final scores,
closing betting lines) from [CollegeFootballData.com](https://collegefootballdata.com/)
— no extra packages needed, it's called directly over `httpx` — then compute
Elo the same way:

```bash
python -m app.scripts.load_historical_cfb_data --seasons 2024 2025
python -m app.scripts.compute_elo --league college
```

Both leagues share the same Elo math (`app/elo.py`) and are independent —
`--league` picks which one to (re)compute; there's no cross-league rating.
`/elo/ratings` and `/elo/value` both take a `league=nfl|college` query param
(default `nfl`).

Live odds use full mascot names ("Ohio State Buckeyes") while each historical
source uses its own convention (nflverse abbreviations for NFL, CFBD's school
name for college — which itself sometimes differs from the live feed, e.g.
CFBD's "App State" vs. the live feed's "Appalachian State Mountaineers").
`app/teams.py` and `app/teams_cfb.py` bridge that gap so Elo ratings actually
match up with live games; `teams_cfb.py` is generated (not hand-typed) from
CFBD's own `/teams` endpoint via `generate_cfb_teams.py`, since guessing 138
schools' mascots and aliases by hand is exactly how you get it wrong. Re-run
the generator if team names drift (conference realignment, rebrands):

```bash
python -m app.scripts.generate_cfb_teams
```

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

## Deploying to production (free tier)

This deploys to three free services: **Neon** (Postgres), **Render** (FastAPI
backend), **Vercel** (React frontend). All three have genuinely free tiers —
no card required for the basics — which is why this combo instead of, say,
Railway (no permanent free tier) or Render's own Postgres (free tier expires
after 90 days, a bad fit for anything meant to stay up).

I can't create these accounts or click through their dashboards for you —
that's exactly the kind of action this assistant is built to not do on your
behalf. Everything below is what you'll do yourself; ask me if any step needs
troubleshooting.

**1. Database — [Neon](https://neon.tech)**
1. Sign up, create a project (any region).
2. Copy the connection string it gives you (starts `postgresql://`, already
   includes `?sslmode=require`). Save it — this is `DATABASE_URL`.

**2. Backend — [Render](https://render.com)**
1. Sign up, connect your GitHub account, select the `ThePulse` repo.
2. Render should detect `render.yaml` at the repo root and offer to create
   the `thepulse-backend` web service from it. If it doesn't, create a new
   **Web Service** manually with: root directory `backend`, build command
   `pip install -r requirements.txt`, start command
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
3. Set these environment variables in the Render dashboard (they're marked
   `sync: false` in `render.yaml`, meaning Render won't set them for you):
   - `ODDS_API_KEY` — your real key
   - `CFBD_API_KEY` — your real key (only needed if you'll run the historical
     pipelines from a shell on Render; skip it if not)
   - `DATABASE_URL` — the Neon connection string from step 1
   - `FRONTEND_ORIGIN` — leave a placeholder for now (e.g. `http://localhost:5173`);
     you'll come back and set this to your real Vercel URL in step 4
4. Deploy. Once it's up, note the URL Render gives you
   (`https://thepulse-backend-xxxx.onrender.com`) — you'll need it for the
   frontend. Confirm it's alive: `curl https://your-render-url/health`.
5. (Optional) Load historical data + Elo so `/elo/*` and the dashboard have
   something to show — open a Render shell for the service and run the same
   commands as local setup (step 2 above): `pip install -r requirements-data.txt`,
   `pip install --no-deps nfl-data-py==0.3.3`, then the `load_historical_*`
   and `compute_elo` commands.

**3. Frontend — [Vercel](https://vercel.com)**
1. Sign up, import the `ThePulse` repo.
2. Set the project's root directory to `frontend`. Vercel auto-detects Vite;
   no build/output config needed (`vercel.json` in `frontend/` handles the
   client-side routing rewrite React Router needs).
3. Set environment variable `VITE_API_BASE_URL` to your Render backend URL
   from step 2.4.
4. Deploy. Note the URL Vercel gives you
   (`https://the-pulse-xxxx.vercel.app`).

**4. Close the loop**
Go back to Render and update `FRONTEND_ORIGIN` to your real Vercel URL, then
redeploy the backend (Render redeploys automatically on an env var change).
Without this, the browser will block API requests with a CORS error.

**Known limitations of the free tier for a resume project:**
- Render's free web service sleeps after ~15 minutes of no traffic and takes
  a few seconds to wake on the next request — expected for a demo, not
  something to "fix."
- While asleep, the APScheduler odds refresh doesn't run (there's no process
  to run it in). Odds refresh on a schedule while the service is awake, and
  once on every cold start via the startup fetch in `main.py`'s lifespan —
  good enough to keep data reasonably fresh for anyone visiting.
- The Odds API free tier is 500 requests/month; each cold start burns one
  request per league. Fine for occasional demo traffic, not for anything with
  real usage.

## API routes

| Method | Route | Description |
|---|---|---|
| GET | `/odds?week={week}&league={nfl\|college}` | Aggregated latest odds per game |
| GET | `/lines?game={id}` | Spread/moneyline/total for one game, grouped by sportsbook |
| POST | `/picks` | Save a pick with odds captured at entry |
| GET | `/picks` | Saved picks, with CLV backfilled once games kick off |
| PATCH | `/picks/{id}/result` | Set a pick's result (win/loss/push) |
| GET | `/stats/dashboard` | Win rate, ROI, avg CLV, CLV trend |
| GET | `/elo/ratings?league={nfl\|college}` | Current Elo ratings by team |
| GET | `/elo/value?league={nfl\|college}` | Upcoming games where Elo diverges from the market |
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
- `/picks` and `/stats/dashboard` backfill closing lines/CLV on every request,
  but only for games that have an unresolved pick — not every started game.
  With thousands of historical games loaded for Elo, recomputing closing
  lines for all of them on every dashboard load isn't just wasted work, it's
  a genuinely bad response time (this was a real regression caught while
  testing: ~17s per request before scoping it down, <150ms after).
