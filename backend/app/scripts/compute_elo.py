"""Runs the Elo model over completed historical games (loaded via
load_historical_data.py / load_historical_cfb_data.py) to build current team
ratings, then compares the Elo-implied win probability against the market's
closing line for each upcoming game to flag potential value. Run with:

    python -m app.scripts.compute_elo --league nfl
    python -m app.scripts.compute_elo --league college
"""

import argparse
import logging

from app import models
from app.database import SessionLocal, init_db
from app.elo import INITIAL_RATING, elo_win_prob, update_ratings
from app.probability import american_to_implied_prob, remove_vig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _to_elo_key(league: str):
    if league == "college":
        from app.teams_cfb import to_elo_key
    else:
        from app.teams import to_elo_key
    return to_elo_key


def compute_ratings(league: str = "nfl") -> dict[str, float]:
    """Replay every completed game for a league in chronological order to derive ratings."""
    db = SessionLocal()
    try:
        games = (
            db.query(models.Game)
            .filter(models.Game.league == league, models.Game.completed.is_(True))
            .order_by(models.Game.commence_time)
            .all()
        )
        ratings: dict[str, float] = {}
        for game in games:
            if game.home_score is None or game.away_score is None:
                continue
            home_rating = ratings.setdefault(game.home_team, INITIAL_RATING)
            away_rating = ratings.setdefault(game.away_team, INITIAL_RATING)
            ratings[game.home_team], ratings[game.away_team] = update_ratings(
                home_rating, away_rating, game.home_score, game.away_score
            )

        for team, rating in ratings.items():
            row = db.get(models.TeamElo, {"team": team, "league": league})
            if row is None:
                row = models.TeamElo(team=team, league=league)
                db.add(row)
            row.rating = rating
        db.commit()
        logger.info("Computed Elo ratings for %d %s teams from %d games.", len(ratings), league, len(games))
        return ratings
    finally:
        db.close()


def find_value_games(league: str = "nfl", week: int | None = None) -> list[dict]:
    """For upcoming (not-yet-completed) games with a moneyline available, compare
    the Elo win probability to the market's vig-free implied probability.
    Optionally scoped to a single week — otherwise this dumps the whole
    season, which isn't a useful "value" view in practice."""
    to_elo_key = _to_elo_key(league)
    db = SessionLocal()
    value_games = []
    try:
        query = db.query(models.Game).filter(
            models.Game.league == league, models.Game.completed.is_(False)
        )
        if week is not None:
            query = query.filter(models.Game.week == week)
        upcoming = query.all()
        ratings = {r.team: r.rating for r in db.query(models.TeamElo).filter_by(league=league).all()}

        for game in upcoming:
            home_ml = next(
                (s.price for s in game.odds_snapshots if s.market == "h2h" and s.side == "home"), None
            )
            away_ml = next(
                (s.price for s in game.odds_snapshots if s.market == "h2h" and s.side == "away"), None
            )
            if home_ml is None or away_ml is None:
                continue
            home_key, away_key = to_elo_key(game.home_team), to_elo_key(game.away_team)
            if home_key not in ratings or away_key not in ratings:
                continue

            elo_prob = elo_win_prob(ratings[home_key], ratings[away_key])
            market_home, market_away = remove_vig(
                american_to_implied_prob(home_ml), american_to_implied_prob(away_ml)
            )
            edge = elo_prob - market_home
            value_games.append(
                {
                    "game_id": game.id,
                    "week": game.week,
                    "matchup": f"{game.away_team} @ {game.home_team}",
                    "elo_home_win_prob": round(elo_prob, 4),
                    "market_home_win_prob": round(market_home, 4),
                    "edge": round(edge, 4),
                }
            )
        value_games.sort(key=lambda g: abs(g["edge"]), reverse=True)
        return value_games
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", choices=["nfl", "college"], default="nfl")
    args = parser.parse_args()

    init_db()
    compute_ratings(args.league)
    for g in find_value_games(args.league):
        logger.info(g)
