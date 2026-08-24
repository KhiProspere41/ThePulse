"""Thin client for The Odds API (https://the-odds-api.com).

Quota model, which drives most of the design here:

  * `/sports/{sport}/odds`                  cost = markets x regions
  * `/sports/{sport}/events/{id}/odds`      cost = markets *returned* x regions

Game lines are one bulk call per league. Player props are per event, so a
single 16-game slate across six markets costs ~96 credits — a fifth of the
free tier's 500/month. Everything discretionary therefore goes through
`have_quota_for()` and is cached aggressively upstream in `app.ingest`.
"""

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

# Anytime-TD is priced Yes/No per player; the rest are Over/Under on a line.
YES_NO_MARKETS = {"player_anytime_td", "player_1st_td", "player_last_td"}


class OddsApiError(RuntimeError):
    """Raised for a non-retryable API failure (bad key, unsupported market)."""


def player_prop_markets() -> list[str]:
    return [m.strip() for m in settings.player_prop_markets.split(",") if m.strip()]


# --- quota -----------------------------------------------------------------

# Last known quota state, refreshed from response headers on every call. Held
# in memory so callers can check it without a DB round-trip; `app.ingest`
# mirrors it into the api_usage table for the dashboard.
last_quota: dict[str, int | str | None] = {
    "requests_used": None,
    "requests_remaining": None,
    "last_cost": None,
    "last_endpoint": None,
}


def _record_quota(resp: httpx.Response, endpoint: str) -> None:
    def _as_int(header: str) -> int | None:
        raw = resp.headers.get(header)
        try:
            return int(raw) if raw is not None else None
        except ValueError:
            return None

    last_quota.update(
        {
            "requests_used": _as_int("x-requests-used"),
            "requests_remaining": _as_int("x-requests-remaining"),
            "last_cost": _as_int("x-requests-last"),
            "last_endpoint": endpoint,
        }
    )
    remaining = last_quota["requests_remaining"]
    if remaining is not None:
        logger.info("Odds API: %s cost %s, %s requests remaining", endpoint, last_quota["last_cost"], remaining)


def have_quota_for(estimated_cost: int) -> bool:
    """Whether a discretionary fetch should be allowed to spend credits.

    Unknown remaining balance (nothing fetched yet this process) is treated as
    "go ahead" — the first call will populate it.
    """
    remaining = last_quota.get("requests_remaining")
    if remaining is None:
        return True
    return int(remaining) - estimated_cost >= settings.odds_api_min_remaining


def _get(path: str, params: dict, endpoint_label: str) -> list[dict] | dict:
    if not settings.odds_api_key:
        logger.warning("ODDS_API_KEY is not set — skipping %s.", endpoint_label)
        return []

    url = f"{settings.odds_api_base_url}{path}"
    params = {"apiKey": settings.odds_api_key, "oddsFormat": "american", "dateFormat": "iso", **params}

    with httpx.Client(timeout=20.0) as client:
        resp = client.get(url, params=params)
        _record_quota(resp, endpoint_label)
        if resp.status_code == 401:
            raise OddsApiError("Odds API rejected the key (401). Check ODDS_API_KEY.")
        if resp.status_code == 422:
            # Typically an unsupported market or sport key for this plan.
            raise OddsApiError(f"Odds API rejected the request (422): {resp.text[:200]}")
        if resp.status_code == 429:
            raise OddsApiError("Odds API quota exhausted (429).")
        resp.raise_for_status()
        return resp.json()


# --- weeks -----------------------------------------------------------------


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


# --- game lines ------------------------------------------------------------


def fetch_odds(league: str) -> list[dict]:
    """Fetch current odds for a league from The Odds API. Returns raw event dicts."""
    sport_key = SPORT_KEYS.get(league)
    if sport_key is None:
        raise ValueError(f"Unknown league '{league}'. Expected one of {list(SPORT_KEYS)}.")

    result = _get(
        f"/sports/{sport_key}/odds",
        {"regions": "us", "markets": MARKETS},
        f"odds:{league}",
    )
    return result if isinstance(result, list) else []


# --- player props ----------------------------------------------------------


def fetch_player_props(event_id: str, league: str = "nfl", markets: list[str] | None = None) -> dict:
    """Player props for one event, from the per-event odds endpoint.

    Returns the raw event dict (with a `bookmakers` list), or an empty dict if
    the books have nothing posted. Props are only billed for markets actually
    returned, so an event with no props posted is effectively free.
    """
    sport_key = SPORT_KEYS.get(league)
    if sport_key is None:
        raise ValueError(f"Unknown league '{league}'.")

    markets = markets or player_prop_markets()
    result = _get(
        f"/sports/{sport_key}/events/{event_id}/odds",
        {"regions": "us", "markets": ",".join(markets)},
        f"props:{event_id}",
    )
    if isinstance(result, dict):
        return result
    return {}


# --- futures / outrights ---------------------------------------------------


def fetch_futures(sport_key: str | None = None) -> list[dict]:
    """Outright (futures) prices, e.g. the NFL Super Bowl winner market.

    Futures live under their own sport key rather than as a market on the
    regular-season feed, and the response is a single pseudo-event whose
    outcomes are teams instead of sides.
    """
    sport_key = sport_key or settings.nfl_futures_sport_key
    result = _get(
        f"/sports/{sport_key}/odds",
        {"regions": "us", "markets": "outrights"},
        f"futures:{sport_key}",
    )
    return result if isinstance(result, list) else []
