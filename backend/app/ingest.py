"""Turns raw Odds API responses into Game / OddsSnapshot rows, and keeps
picks' closing lines + CLV up to date."""

import datetime as dt
import logging

from sqlalchemy.orm import Session

from app import models
from app.odds_api import fetch_odds, week_for_commence_time
from app.probability import american_to_implied_prob

logger = logging.getLogger(__name__)


def _side_for_outcome(outcome_name: str, market: str, home_team: str, away_team: str) -> str | None:
    if market == "totals":
        return outcome_name.lower() if outcome_name.lower() in ("over", "under") else None
    if outcome_name == home_team:
        return "home"
    if outcome_name == away_team:
        return "away"
    return None


def ingest_league(db: Session, league: str) -> int:
    """Fetch current odds for a league and persist games + a fresh odds snapshot.
    Returns the number of games ingested."""
    events = fetch_odds(league)
    now = dt.datetime.utcnow()

    for event in events:
        commence_time = dt.datetime.fromisoformat(event["commence_time"].replace("Z", "+00:00")).replace(
            tzinfo=None
        )
        game = db.get(models.Game, event["id"])
        if game is None:
            game = models.Game(
                id=event["id"],
                league=league,
                week=week_for_commence_time(commence_time),
                commence_time=commence_time,
                home_team=event["home_team"],
                away_team=event["away_team"],
            )
            db.add(game)
        else:
            game.commence_time = commence_time

        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                for outcome in market.get("outcomes", []):
                    side = _side_for_outcome(outcome["name"], market["key"], game.home_team, game.away_team)
                    if side is None:
                        continue
                    db.add(
                        models.OddsSnapshot(
                            game_id=game.id,
                            bookmaker=bookmaker["key"],
                            market=market["key"],
                            side=side,
                            price=int(outcome["price"]),
                            point=outcome.get("point"),
                            fetched_at=now,
                        )
                    )

    db.commit()
    logger.info("Ingested %d %s games at %s", len(events), league, now.isoformat())
    return len(events)


def refresh_all_leagues(db: Session) -> None:
    for league in ("nfl", "college"):
        try:
            ingest_league(db, league)
        except Exception:
            logger.exception("Failed to ingest odds for league=%s", league)


def update_closing_lines_and_clv(db: Session) -> int:
    """For any game that has started, mark each bookmaker/market/side's most recent
    snapshot before kickoff as the closing line, then backfill CLV on picks."""
    now = dt.datetime.utcnow()
    started_games = db.query(models.Game).filter(models.Game.commence_time <= now).all()
    updated = 0

    for game in started_games:
        snapshots = (
            db.query(models.OddsSnapshot)
            .filter(
                models.OddsSnapshot.game_id == game.id,
                models.OddsSnapshot.fetched_at <= game.commence_time,
            )
            .order_by(models.OddsSnapshot.fetched_at.desc())
            .all()
        )
        latest_by_key: dict[tuple[str, str, str], models.OddsSnapshot] = {}
        for snap in snapshots:
            key = (snap.bookmaker, snap.market, snap.side)
            if key not in latest_by_key:
                latest_by_key[key] = snap
                if not snap.is_closing:
                    snap.is_closing = True
                    updated += 1

        for pick in game.picks:
            if pick.closing_price is not None:
                continue
            closing = _find_closing_for_pick(latest_by_key, pick, game)
            if closing is None:
                continue
            pick.closing_price = closing.price
            pick.closing_point = closing.point
            pick.clv = _calc_clv(pick.entry_price, closing.price)

    db.commit()
    return updated


def _side_for_pick(pick: models.Pick, game: models.Game) -> str | None:
    if pick.market == "totals":
        return pick.selection.lower() if pick.selection.lower() in ("over", "under") else None
    if pick.selection == game.home_team:
        return "home"
    if pick.selection == game.away_team:
        return "away"
    return None


def _find_closing_for_pick(
    latest_by_key: dict[tuple[str, str, str], models.OddsSnapshot], pick: models.Pick, game: models.Game
) -> models.OddsSnapshot | None:
    side = _side_for_pick(pick, game)
    if side is None:
        return None
    for (bookmaker, market, snap_side), snap in latest_by_key.items():
        if market != pick.market or snap_side != side:
            continue
        if pick.market != "totals" and pick.point is not None and snap.point != pick.point:
            continue
        return snap
    return None


def _calc_clv(entry_price: int, closing_price: int) -> float:
    """Closing Line Value: how much the market moved toward your pick after you
    took it, in percentage points of implied win probability. Positive means the
    closing implied probability for your side is higher than it was when you bet
    (i.e. you got a better price than the market's final number)."""
    entry_prob = american_to_implied_prob(entry_price)
    closing_prob = american_to_implied_prob(closing_price)
    return round((closing_prob - entry_prob) * 100, 2)
