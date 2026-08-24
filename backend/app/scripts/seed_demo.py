"""Seed a runnable demo dataset — no Odds API key required.

The free tier is 500 requests/month and player props are billed per market per
event, so burning credits just to see the UI is a bad trade. This writes a
self-contained slate: Elo ratings for all 32 teams, one week of games with
lines, player props on every game, and a Super Bowl futures board.

    python -m app.scripts.seed_demo
    python -m app.scripts.seed_demo --clear   # remove demo rows and stop

Everything it writes is deterministic (fixed RNG seed) and clearly marked:
game ids start with `demo_`, `Game.source` is `demo`, and every bookmaker is
named `demo_*` so synthetic prices can never be mistaken for real ones in the
UI or mixed into a real database by accident.
"""

import argparse
import datetime as dt
import logging
import random

from app import models
from app.config import settings
from app.database import SessionLocal, init_db
from app.divisions import ALL_TEAMS, normalize
from app.teams import ODDS_API_NAME_TO_ABBR, to_elo_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEMO_PREFIX = "demo_"
DEMO_BOOKS = ("demo_draftkings", "demo_fanduel", "demo_betmgm")
ABBR_TO_NAME = {abbr: name for name, abbr in ODDS_API_NAME_TO_ABBR.items()}

# A few recognisable names per position group, purely so the props table has
# something to render. Not tied to real rosters.
DEMO_PLAYERS = {
    "qb": ["{city} QB1"],
    "rb": ["{city} RB1", "{city} RB2"],
    "wr": ["{city} WR1", "{city} WR2", "{city} TE1"],
}

PROP_SPECS = [
    # market, position group, line centre, line spread, yes/no?
    ("player_pass_yds", "qb", 245.0, 35.0, False),
    ("player_pass_tds", "qb", 1.5, 0.5, False),
    ("player_rush_yds", "rb", 58.5, 22.0, False),
    ("player_reception_yds", "wr", 52.5, 20.0, False),
    ("player_receptions", "wr", 4.5, 1.5, False),
    ("player_anytime_td", "wr", None, None, True),
]


def _american_from_prob(prob: float) -> int:
    """Turn a probability into a plausible American price, with ~4.5% vig."""
    prob = min(max(prob * 1.045, 0.02), 0.95)
    if prob >= 0.5:
        return -int(round(100 * prob / (1 - prob) / 5) * 5)
    return int(round(100 * (1 - prob) / prob / 5) * 5)


def clear_demo(db) -> None:
    game_ids = [g.id for g in db.query(models.Game).filter(models.Game.source == "demo").all()]
    if game_ids:
        db.query(models.PlayerPropSnapshot).filter(
            models.PlayerPropSnapshot.game_id.in_(game_ids)
        ).delete(synchronize_session=False)
        db.query(models.PropsFetch).filter(models.PropsFetch.game_id.in_(game_ids)).delete(
            synchronize_session=False
        )
        db.query(models.OddsSnapshot).filter(models.OddsSnapshot.game_id.in_(game_ids)).delete(
            synchronize_session=False
        )
        db.query(models.Pick).filter(models.Pick.game_id.in_(game_ids)).delete(synchronize_session=False)
        db.query(models.Game).filter(models.Game.id.in_(game_ids)).delete(synchronize_session=False)
    db.query(models.FuturesSnapshot).filter(
        models.FuturesSnapshot.bookmaker.like("demo_%")
    ).delete(synchronize_session=False)
    db.commit()
    logger.info("Cleared %d demo games and their odds, props and futures.", len(game_ids))


def seed(seed_value: int = 7) -> None:
    init_db()
    rng = random.Random(seed_value)
    db = SessionLocal()
    now = dt.datetime.utcnow()

    try:
        clear_demo(db)

        # 1. Elo ratings — a plausible spread around the 1500 baseline, so the
        #    season simulator has something to work with. Real ratings computed
        #    from real history are never overwritten: losing those to demo noise
        #    would be a much worse outcome than an unseeded demo.
        existing_ratings = db.query(models.TeamElo).filter_by(league="nfl").all()
        ratings = {normalize(to_elo_key(r.team)): r.rating for r in existing_ratings}
        if ratings:
            logger.info("Keeping %d existing Elo ratings — not overwriting them.", len(ratings))
            for team in ALL_TEAMS:
                ratings.setdefault(team, 1500.0)
        else:
            for team in ALL_TEAMS:
                rating = round(rng.gauss(1500, 65), 1)
                ratings[team] = rating
                db.add(models.TeamElo(team=team, league="nfl", rating=rating, updated_at=now))

        # 2. Games. If the odds feed has already loaded real upcoming games,
        #    hang the demo props off those rather than inventing a parallel
        #    slate — duplicate matchups would push teams past 17 games and skew
        #    the simulator's win ladder.
        existing_games = (
            db.query(models.Game)
            .filter(
                models.Game.league == "nfl",
                models.Game.source != "demo",
                models.Game.completed.is_(False),
            )
            .order_by(models.Game.commence_time)
            .limit(16)
            .all()
        )
        if existing_games:
            logger.info("Found %d real upcoming games — seeding props onto those.", len(existing_games))
            for game in existing_games:
                _seed_props(
                    db,
                    rng,
                    game.id,
                    normalize(to_elo_key(game.home_team)),
                    normalize(to_elo_key(game.away_team)),
                    now,
                )
            _seed_futures(db, rng, ratings, now)
            db.commit()
            logger.info("Seeded demo props for %d games and a Super Bowl board.", len(existing_games))
            return

        teams = list(ALL_TEAMS)
        rng.shuffle(teams)
        kickoff = settings.nfl_season_start
        week = 1
        games = 0

        for i in range(0, len(teams) - 1, 2):
            home, away = teams[i], teams[i + 1]
            game_id = f"{DEMO_PREFIX}{home}_{away}_{week}"
            rating_gap = ratings[home] + 55 - ratings[away]
            spread = round(-rating_gap / 25 * 2) / 2  # Elo points -> points, to the half
            total = round(rng.uniform(38, 51) * 2) / 2
            home_win_prob = 1 / (1 + 10 ** (-rating_gap / 400))

            game = models.Game(
                id=game_id,
                league="nfl",
                season=kickoff.year,
                week=week,
                commence_time=kickoff + dt.timedelta(hours=rng.choice([0, 3, 27, 51])),
                home_team=ABBR_TO_NAME.get(home, home),
                away_team=ABBR_TO_NAME.get(away, away),
                completed=False,
                source="demo",
            )
            db.add(game)
            games += 1

            for book in DEMO_BOOKS:
                jitter = rng.uniform(-0.5, 0.5)
                for market, side, price, point in (
                    ("h2h", "home", _american_from_prob(home_win_prob), None),
                    ("h2h", "away", _american_from_prob(1 - home_win_prob), None),
                    ("spreads", "home", -110 - int(jitter * 10), spread + jitter / 2),
                    ("spreads", "away", -110 + int(jitter * 10), -(spread + jitter / 2)),
                    ("totals", "over", -110, total + jitter / 2),
                    ("totals", "under", -110, total + jitter / 2),
                ):
                    db.add(
                        models.OddsSnapshot(
                            game_id=game_id,
                            bookmaker=book,
                            market=market,
                            side=side,
                            price=int(price),
                            point=point,
                            fetched_at=now,
                        )
                    )

            _seed_props(db, rng, game_id, home, away, now)

        # 3. Super Bowl futures, priced off the same ratings so the model-vs-
        #    market view has something coherent to compare against.
        _seed_futures(db, rng, ratings, now)

        db.commit()
        logger.info(
            "Seeded %d demo games with lines and props, Elo for %d teams, and a Super Bowl board.",
            games,
            len(ALL_TEAMS),
        )
    finally:
        db.close()


def _seed_futures(db, rng: random.Random, ratings: dict[str, float], now: dt.datetime) -> None:
    """A Super Bowl board with realistic hold: each book's implied
    probabilities are deliberately noised so they sum to well over 1, which is
    what the devigging in `routers/futures.py` exists to undo."""
    strength = {t: 10 ** (ratings[t] / 400) for t in ALL_TEAMS}
    denominator = sum(strength.values())
    for book in DEMO_BOOKS:
        for team in ALL_TEAMS:
            fair = strength[team] / denominator
            noisy = max(0.004, fair * rng.uniform(0.7, 1.35))
            db.add(
                models.FuturesSnapshot(
                    league="nfl",
                    sport_key=settings.nfl_futures_sport_key,
                    market="outrights",
                    team=ABBR_TO_NAME.get(team, team),
                    bookmaker=book,
                    price=_american_from_prob(noisy),
                    fetched_at=now,
                )
            )


def _seed_props(db, rng: random.Random, game_id: str, home: str, away: str, now: dt.datetime) -> None:
    for team in (home, away):
        city = ABBR_TO_NAME.get(team, team).rsplit(" ", 1)[0]
        for market, group, centre, spread, yes_no in PROP_SPECS:
            for template in DEMO_PLAYERS[group]:
                player = template.format(city=city)
                if yes_no:
                    prob = rng.uniform(0.18, 0.55)
                    for side, p in (("yes", prob), ("no", 1 - prob)):
                        for book in DEMO_BOOKS:
                            db.add(
                                models.PlayerPropSnapshot(
                                    game_id=game_id,
                                    bookmaker=book,
                                    market=market,
                                    player=player,
                                    side=side,
                                    price=_american_from_prob(p * rng.uniform(0.95, 1.05)),
                                    point=None,
                                    fetched_at=now,
                                )
                            )
                    continue

                line = round(rng.gauss(centre, spread) * 2) / 2
                line = max(0.5, line)
                for book in DEMO_BOOKS:
                    book_line = line + rng.choice([-0.5, 0, 0, 0.5])
                    for side in ("over", "under"):
                        db.add(
                            models.PlayerPropSnapshot(
                                game_id=game_id,
                                bookmaker=book,
                                market=market,
                                player=player,
                                side=side,
                                price=_american_from_prob(rng.uniform(0.47, 0.55)),
                                point=book_line,
                                fetched_at=now,
                            )
                        )

    # Mark the cache as warm so opening the game page doesn't try to spend
    # credits refreshing props that were never real to begin with.
    marker = db.get(models.PropsFetch, game_id)
    if marker is None:
        marker = models.PropsFetch(game_id=game_id)
        db.add(marker)
    marker.fetched_at = now
    marker.outcome_count = 0
    marker.error = None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clear", action="store_true", help="Remove demo rows and exit")
    parser.add_argument("--seed", type=int, default=7, help="RNG seed")
    args = parser.parse_args()

    if args.clear:
        init_db()
        db = SessionLocal()
        try:
            clear_demo(db)
        finally:
            db.close()
    else:
        seed(args.seed)
