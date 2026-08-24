"""Pulls the last 2 completed college football (FBS) seasons — schedules,
final scores, and closing betting lines — from the CollegeFootballData.com
REST API and loads them into the games / odds_snapshots tables. Run with:

    python -m app.scripts.load_historical_cfb_data --seasons 2024 2025

Requires a free API key from https://collegefootballdata.com/key set as
CFBD_API_KEY in backend/.env.

Talks to the API directly via httpx rather than the official `cfbd` SDK: that
package pins pydantic<2, which conflicts with FastAPI/pydantic-settings in
this project (its generated models use pydantic v1 syntax, so it's a real
incompatibility, not just a stale version pin — see requirements-data.txt).
"""

import argparse
import datetime as dt
import logging

import httpx

from app import models
from app.config import settings
from app.database import SessionLocal, init_db
from app.odds_api import week_for_commence_time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CFBD_BASE_URL = "https://api.collegefootballdata.com"
DEFAULT_SPREAD_ODDS = -110
DEFAULT_TOTAL_ODDS = -110


def _to_naive_utc(iso_str: str) -> dt.datetime:
    value = dt.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return value.astimezone(dt.timezone.utc).replace(tzinfo=None)


def _client() -> httpx.Client:
    if not settings.cfbd_api_key:
        raise RuntimeError("CFBD_API_KEY is not set — get a free key at https://collegefootballdata.com/key")
    return httpx.Client(
        base_url=CFBD_BASE_URL,
        headers={"Authorization": f"Bearer {settings.cfbd_api_key}"},
        timeout=30.0,
    )


def load_seasons(seasons: list[int]) -> None:
    init_db()
    db = SessionLocal()
    games_loaded = 0
    snapshots_loaded = 0

    try:
        with _client() as client:
            for season in seasons:
                logger.info("Fetching CFB games for season %d", season)
                games_resp = client.get(
                    "/games", params={"year": season, "seasonType": "regular", "classification": "fbs"}
                )
                games_resp.raise_for_status()
                games = games_resp.json()

                lines_resp = client.get("/lines", params={"year": season, "seasonType": "regular"})
                lines_resp.raise_for_status()
                lines_by_game_id = {bg["id"]: bg.get("lines", []) for bg in lines_resp.json()}

                for g in games:
                    if not g.get("startDate"):
                        continue
                    game_id = f"cfb_hist_{g['id']}"
                    commence_time = _to_naive_utc(g["startDate"])

                    game = db.get(models.Game, game_id)
                    if game is None:
                        game = models.Game(id=game_id, league="college", source="historical")
                        db.add(game)

                    game.season = g["season"]
                    game.week = g["week"] if g.get("week") is not None else week_for_commence_time(
                        commence_time, "college"
                    )
                    game.commence_time = commence_time
                    game.home_team = g["homeTeam"]
                    game.away_team = g["awayTeam"]
                    game.home_score = g.get("homePoints")
                    game.away_score = g.get("awayPoints")
                    game.completed = bool(g.get("completed"))
                    games_loaded += 1

                    for line in lines_by_game_id.get(g["id"], []):
                        provider = (line.get("provider") or "consensus").lower().replace(" ", "_")
                        snaps = []
                        if line.get("homeMoneyline") is not None:
                            snaps.append(("h2h", "home", int(line["homeMoneyline"]), None))
                        if line.get("awayMoneyline") is not None:
                            snaps.append(("h2h", "away", int(line["awayMoneyline"]), None))
                        if line.get("spread") is not None:
                            snaps.append(("spreads", "home", DEFAULT_SPREAD_ODDS, float(line["spread"])))
                            snaps.append(("spreads", "away", DEFAULT_SPREAD_ODDS, -float(line["spread"])))
                        if line.get("overUnder") is not None:
                            snaps.append(("totals", "over", DEFAULT_TOTAL_ODDS, float(line["overUnder"])))
                            snaps.append(("totals", "under", DEFAULT_TOTAL_ODDS, float(line["overUnder"])))

                        for market, side, price, point in snaps:
                            db.add(
                                models.OddsSnapshot(
                                    game_id=game_id,
                                    bookmaker=provider,
                                    market=market,
                                    side=side,
                                    price=price,
                                    point=point,
                                    fetched_at=dt.datetime.utcnow(),
                                    is_closing=True,
                                )
                            )
                            snapshots_loaded += 1

        db.commit()
        logger.info("Loaded %d games and %d odds snapshots.", games_loaded, snapshots_loaded)
    finally:
        db.close()


if __name__ == "__main__":
    current_year = dt.date.today().year
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seasons",
        type=int,
        nargs="+",
        default=[current_year - 2, current_year - 1],
        help="Season years to load, e.g. --seasons 2024 2025",
    )
    args = parser.parse_args()
    load_seasons(args.seasons)
