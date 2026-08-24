"""Pulls the last 2 completed NFL seasons (schedules, final scores, and closing
Vegas lines) via nfl-data-py and loads them into the games / odds_snapshots
tables. Run with: python -m app.scripts.load_historical_data [--seasons 2024 2025]

nfl-data-py sources its schedule data (including historical betting lines)
from Pro-Football-Reference / nflverse's public datasets.
"""

import argparse
import datetime as dt
import logging

import nfl_data_py as nfl
import pandas as pd

from app import models
from app.database import SessionLocal, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _game_id(row) -> str:
    return f"hist_{row.game_id}"


def _or_default(value, default):
    return default if value is None or (isinstance(value, float) and pd.isna(value)) else value


def _to_snapshot(game_id: str, bookmaker: str, market: str, side: str, price, point=None):
    if price is None or (isinstance(price, float) and pd.isna(price)):
        return None
    return models.OddsSnapshot(
        game_id=game_id,
        bookmaker=bookmaker,
        market=market,
        side=side,
        price=int(price),
        point=None if point is None or (isinstance(point, float) and pd.isna(point)) else float(point),
        fetched_at=dt.datetime.utcnow(),
        is_closing=True,
    )


def load_seasons(seasons: list[int]) -> None:
    init_db()
    logger.info("Fetching NFL schedules for seasons: %s", seasons)
    schedules = nfl.import_schedules(seasons)

    db = SessionLocal()
    games_loaded = 0
    snapshots_loaded = 0
    try:
        for row in schedules.itertuples():
            game_id = _game_id(row)
            completed = pd.notna(getattr(row, "home_score", None))

            game = db.get(models.Game, game_id)
            if game is None:
                game = models.Game(id=game_id, league="nfl", source="historical")
                db.add(game)

            game.season = int(row.season)
            game.week = int(row.week)
            game.commence_time = pd.to_datetime(row.gameday).to_pydatetime()
            game.home_team = row.home_team
            game.away_team = row.away_team
            game.home_score = None if pd.isna(row.home_score) else int(row.home_score)
            game.away_score = None if pd.isna(row.away_score) else int(row.away_score)
            game.completed = bool(completed)
            games_loaded += 1

            # Closing Vegas lines, as a single "vegas_consensus" bookmaker.
            snaps = [
                _to_snapshot(game_id, "vegas_consensus", "h2h", "home", getattr(row, "home_moneyline", None)),
                _to_snapshot(game_id, "vegas_consensus", "h2h", "away", getattr(row, "away_moneyline", None)),
                _to_snapshot(
                    game_id,
                    "vegas_consensus",
                    "spreads",
                    "home",
                    _or_default(getattr(row, "home_spread_odds", None), -110),
                    getattr(row, "spread_line", None),
                ),
                _to_snapshot(
                    game_id,
                    "vegas_consensus",
                    "spreads",
                    "away",
                    _or_default(getattr(row, "away_spread_odds", None), -110),
                    -row.spread_line if pd.notna(getattr(row, "spread_line", None)) else None,
                ),
                _to_snapshot(
                    game_id,
                    "vegas_consensus",
                    "totals",
                    "over",
                    _or_default(getattr(row, "over_odds", None), -110),
                    getattr(row, "total_line", None),
                ),
                _to_snapshot(
                    game_id,
                    "vegas_consensus",
                    "totals",
                    "under",
                    _or_default(getattr(row, "under_odds", None), -110),
                    getattr(row, "total_line", None),
                ),
            ]
            for snap in snaps:
                if snap is not None:
                    db.add(snap)
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
