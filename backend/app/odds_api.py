"""Thin client for The Odds API (https://the-odds-api.com)."""

import datetime as dt
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SPORT_KEYS = {
    "nfl": "americanfootball_nfl",
    "college": "americanfootball_ncaaf",
}

MARKETS = "h2h,spreads,totals"


def week_for_commence_time(commence_time: dt.datetime, league: str = "nfl") -> int:
    """Best-effort week number derived from kickoff date and each league's own
    season-start anchor. College has a "week 0" slate the weekend before its
    week 1 anchor, so college weeks are allowed to floor at 0; the NFL has no
    such week, so it floors at 1."""
    if league == "college":
        delta_days = (commence_time - settings.cfb_season_start).days
        return max(0, delta_days // 7 + 1)
    delta_days = (commence_time - settings.nfl_season_start).days
    return max(1, delta_days // 7 + 1)


def fetch_odds(league: str) -> list[dict]:
    """Fetch current odds for a league from The Odds API. Returns raw event dicts."""
    sport_key = SPORT_KEYS.get(league)
    if sport_key is None:
        raise ValueError(f"Unknown league '{league}'. Expected one of {list(SPORT_KEYS)}.")

    if not settings.odds_api_key:
        logger.warning("ODDS_API_KEY is not set — returning no odds.")
        return []

    url = f"{settings.odds_api_base_url}/sports/{sport_key}/odds"
    params = {
        "apiKey": settings.odds_api_key,
        "regions": "us",
        "markets": MARKETS,
        "oddsFormat": "american",
        "dateFormat": "iso",
    }
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        remaining = resp.headers.get("x-requests-remaining")
        if remaining is not None:
            logger.info("Odds API requests remaining this period: %s", remaining)
        return resp.json()
