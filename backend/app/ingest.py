"""Turns raw Odds API responses into Game / OddsSnapshot rows, and keeps
picks' closing lines + CLV up to date."""

import datetime as dt
import logging

from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.odds_api import (
    YES_NO_MARKETS,
    fetch_futures,
    fetch_odds,
    fetch_player_props,
    have_quota_for,
    last_quota,
    player_prop_markets,
    week_for_commence_time,
)
from app.probability import american_to_implied_prob

logger = logging.getLogger(__name__)


def season_for_commence_time(commence_time: dt.datetime) -> int:
    """NFL season a kickoff belongs to. Seasons straddle New Year, so January
    and February games belong to the season that started the previous autumn."""
    return commence_time.year if commence_time.month >= 3 else commence_time.year - 1


def record_api_usage(db: Session) -> None:
    """Mirror the client's in-memory quota headers into the api_usage table so
    the dashboard can show how much of the monthly allowance is left."""
    if last_quota.get("requests_remaining") is None and last_quota.get("requests_used") is None:
        return
    row = db.get(models.ApiUsage, 1)
    if row is None:
        row = models.ApiUsage(id=1)
        db.add(row)
    row.requests_used = last_quota.get("requests_used")
    row.requests_remaining = last_quota.get("requests_remaining")
    row.last_cost = last_quota.get("last_cost")
    row.last_endpoint = last_quota.get("last_endpoint")
    row.updated_at = dt.datetime.utcnow()


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
                season=season_for_commence_time(commence_time),
                week=week_for_commence_time(commence_time, league),
                commence_time=commence_time,
                home_team=event["home_team"],
                away_team=event["away_team"],
            )
            db.add(game)
        else:
            game.commence_time = commence_time
            game.week = week_for_commence_time(commence_time, league)
            game.season = season_for_commence_time(commence_time)

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

    record_api_usage(db)
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
    """For any started game with a pick still missing its closing line, mark
    each bookmaker/market/side's most recent snapshot before kickoff as the
    closing line, then backfill CLV on that pick.

    Scoped to games with an unresolved pick (rather than every started game)
    because this runs on every GET /picks and /stats/dashboard request — with
    thousands of historical games loaded for Elo/backtesting, recomputing
    closing lines for all of them on every request is a needless N+1 cost
    that has nothing to do with picks a user actually made.
    """
    now = dt.datetime.utcnow()
    games_needing_backfill = (
        db.query(models.Game)
        .join(models.Pick)
        .filter(
            models.Game.commence_time <= now,
            models.Pick.closing_price.is_(None),
            # Futures picks have no game and no kickoff, so nothing to close
            # against; the inner join already excludes them, but be explicit.
            models.Pick.bet_type != "futures",
        )
        .distinct()
        .all()
    )
    updated = 0

    for game in games_needing_backfill:
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

        prop_pick_pending = any(
            p.closing_price is None and p.bet_type == "player_prop" for p in game.picks
        )
        latest_prop_by_key: dict[tuple, models.PlayerPropSnapshot] = {}
        if prop_pick_pending:
            prop_snapshots = (
                db.query(models.PlayerPropSnapshot)
                .filter(
                    models.PlayerPropSnapshot.game_id == game.id,
                    models.PlayerPropSnapshot.fetched_at <= game.commence_time,
                )
                .order_by(models.PlayerPropSnapshot.fetched_at.desc())
                .all()
            )
            for snap in prop_snapshots:
                key = (snap.bookmaker, snap.market, snap.player, snap.side)
                if key not in latest_prop_by_key:
                    latest_prop_by_key[key] = snap
                    if not snap.is_closing:
                        snap.is_closing = True
                        updated += 1

        for pick in game.picks:
            if pick.closing_price is not None:
                continue
            if pick.bet_type == "player_prop":
                closing = _find_closing_for_prop_pick(latest_prop_by_key, pick)
            else:
                closing = _find_closing_for_pick(latest_by_key, pick, game)
            if closing is None:
                continue
            pick.closing_price = closing.price
            pick.closing_point = closing.point
            pick.clv = _calc_clv(pick.entry_price, closing.price)

    db.commit()
    return updated


def _find_closing_for_prop_pick(
    latest_by_key: dict[tuple, models.PlayerPropSnapshot], pick: models.Pick
) -> models.PlayerPropSnapshot | None:
    """Closing price for a player-prop pick.

    Matched on player + market + side but deliberately *not* on the line: books
    move a prop by shifting the number as often as the price, so requiring an
    exact `point` match would leave most prop picks with no closing line at all.
    The resulting CLV is therefore price-only and understates line movement —
    noted here so the number isn't read as more precise than it is.
    """
    if not pick.player:
        return None
    side = (pick.selection or "").lower()
    for (_bookmaker, market, player, snap_side), snap in latest_by_key.items():
        if market != pick.market or snap_side != side or player != pick.player:
            continue
        return snap
    return None


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


# --- player props ----------------------------------------------------------


def _prop_side(outcome_name: str, market: str) -> str | None:
    """Normalize an outcome's name to a side.

    Over/Under markets carry a line in `point`; anytime/first/last touchdown
    markets are priced Yes/No on the player instead.
    """
    name = (outcome_name or "").strip().lower()
    if market in YES_NO_MARKETS:
        return name if name in ("yes", "no") else None
    return name if name in ("over", "under") else None


def props_are_fresh(db: Session, game_id: str) -> bool:
    marker = db.get(models.PropsFetch, game_id)
    if marker is None:
        return False
    age = dt.datetime.utcnow() - marker.fetched_at
    return age < dt.timedelta(hours=settings.player_props_cache_hours)


def ingest_player_props(db: Session, game_id: str, force: bool = False) -> dict:
    """Fetch and store player props for one game, honouring the cache.

    Returns a small status dict describing what happened, so the API can tell
    the UI whether it served cached data, spent credits, or was held back by
    the quota floor. Never raises for an API problem: a game page with stale
    props is a much better outcome than a 500.
    """
    game = db.get(models.Game, game_id)
    if game is None:
        return {"status": "not_found", "outcomes": 0}
    if game.league != "nfl":
        return {"status": "unsupported_league", "outcomes": 0}

    marker = db.get(models.PropsFetch, game_id)

    if not force and props_are_fresh(db, game_id):
        return {"status": "cached", "outcomes": marker.outcome_count if marker else 0,
                "fetched_at": marker.fetched_at if marker else None}

    # Worst case we are billed one credit per requested market, in one region.
    estimated_cost = len(player_prop_markets())
    if not have_quota_for(estimated_cost):
        logger.warning("Skipping props for %s — quota floor reached.", game_id)
        return {
            "status": "quota_guard",
            "outcomes": marker.outcome_count if marker else 0,
            "fetched_at": marker.fetched_at if marker else None,
        }

    now = dt.datetime.utcnow()
    try:
        event = fetch_player_props(game_id, league="nfl")
        error = None
    except Exception as exc:  # noqa: BLE001 — any API problem degrades to cached data
        logger.warning("Props fetch failed for %s: %s", game_id, exc)
        event, error = {}, str(exc)[:200]

    outcomes = 0
    if event:
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                market_key = market.get("key", "")
                if not market_key.startswith("player_"):
                    continue
                for outcome in market.get("outcomes", []):
                    side = _prop_side(outcome.get("name"), market_key)
                    player = outcome.get("description")
                    if side is None or not player or outcome.get("price") is None:
                        continue
                    db.add(
                        models.PlayerPropSnapshot(
                            game_id=game_id,
                            bookmaker=bookmaker["key"],
                            market=market_key,
                            player=player,
                            side=side,
                            price=int(outcome["price"]),
                            point=outcome.get("point"),
                            fetched_at=now,
                        )
                    )
                    outcomes += 1

    # Always stamp the marker, even on an empty or failed fetch, so a game with
    # no props posted isn't re-requested (and re-billed) on every page view.
    if marker is None:
        marker = models.PropsFetch(game_id=game_id)
        db.add(marker)
    marker.fetched_at = now
    marker.outcome_count = outcomes
    marker.error = error

    record_api_usage(db)
    db.commit()
    logger.info("Ingested %d player-prop outcomes for game %s", outcomes, game_id)
    return {
        "status": "error" if error else "fetched",
        "outcomes": outcomes,
        "fetched_at": now,
        "error": error,
    }


def latest_player_props(db: Session, game_id: str) -> list[models.PlayerPropSnapshot]:
    """Most recent snapshot per (bookmaker, market, player, side, point)."""
    snapshots = (
        db.query(models.PlayerPropSnapshot)
        .filter(models.PlayerPropSnapshot.game_id == game_id)
        .order_by(models.PlayerPropSnapshot.fetched_at.desc())
        .all()
    )
    latest: dict[tuple, models.PlayerPropSnapshot] = {}
    for snap in snapshots:
        latest.setdefault((snap.bookmaker, snap.market, snap.player, snap.side, snap.point), snap)
    return list(latest.values())


# --- futures ---------------------------------------------------------------


def futures_are_fresh(db: Session, sport_key: str) -> bool:
    latest = (
        db.query(models.FuturesSnapshot.fetched_at)
        .filter(models.FuturesSnapshot.sport_key == sport_key)
        .order_by(models.FuturesSnapshot.fetched_at.desc())
        .first()
    )
    if latest is None:
        return False
    return dt.datetime.utcnow() - latest[0] < dt.timedelta(hours=settings.futures_refresh_interval_hours)


def ingest_futures(db: Session, sport_key: str | None = None, force: bool = False) -> dict:
    """Fetch the NFL Super Bowl winner outrights market.

    One credit per refresh, so this is scheduled daily rather than hourly and
    still respects the quota floor.
    """
    sport_key = sport_key or settings.nfl_futures_sport_key

    if not force and futures_are_fresh(db, sport_key):
        return {"status": "cached", "outcomes": 0}
    if not have_quota_for(1):
        logger.warning("Skipping futures — quota floor reached.")
        return {"status": "quota_guard", "outcomes": 0}

    now = dt.datetime.utcnow()
    try:
        events = fetch_futures(sport_key)
        error = None
    except Exception as exc:  # noqa: BLE001 — degrade to cached data
        logger.warning("Futures fetch failed for %s: %s", sport_key, exc)
        events, error = [], str(exc)[:200]

    outcomes = 0
    for event in events:
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market.get("key") != "outrights":
                    continue
                for outcome in market.get("outcomes", []):
                    if outcome.get("price") is None or not outcome.get("name"):
                        continue
                    db.add(
                        models.FuturesSnapshot(
                            league="nfl",
                            sport_key=sport_key,
                            market="outrights",
                            team=outcome["name"],
                            bookmaker=bookmaker["key"],
                            price=int(outcome["price"]),
                            fetched_at=now,
                        )
                    )
                    outcomes += 1

    record_api_usage(db)
    db.commit()
    logger.info("Ingested %d futures prices for %s", outcomes, sport_key)
    return {"status": "error" if error else "fetched", "outcomes": outcomes, "error": error}


def latest_futures(db: Session, sport_key: str | None = None) -> list[models.FuturesSnapshot]:
    """Most recent price per (bookmaker, team) for a futures market."""
    sport_key = sport_key or settings.nfl_futures_sport_key
    snapshots = (
        db.query(models.FuturesSnapshot)
        .filter(models.FuturesSnapshot.sport_key == sport_key)
        .order_by(models.FuturesSnapshot.fetched_at.desc())
        .all()
    )
    latest: dict[tuple[str, str], models.FuturesSnapshot] = {}
    for snap in snapshots:
        latest.setdefault((snap.bookmaker, snap.team), snap)
    return list(latest.values())
