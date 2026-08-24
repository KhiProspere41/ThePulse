"""NFL player season stat leaderboards, and a simple stats-based model for
MVP / Offensive Player of the Year / Defensive Player of the Year.

There is no real odds market for any of these — The Odds API's only NFL
futures market is the Super Bowl winner (see routers/futures.py). "Award
favorites" here are a transparent statistical ranking, not a prediction of
actual voting; the `methodology` field on /player-stats/awards says exactly
how each list is built so it's never mistaken for a market price.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.database import get_db

router = APIRouter(tags=["player-stats"])

CATEGORY_SORT = {
    "overall": lambda r: r.fantasy_points_ppr,
    "passing": lambda r: r.passing_yards,
    "rushing": lambda r: r.rushing_yards,
    "receiving": lambda r: r.receiving_yards,
    # Sacks alone, not the DPOY composite below — a "leaders" list should be
    # one clean stat like every other category. A weighted composite here
    # just becomes a tackle-volume leaderboard (elite tackle totals run
    # 120-160 vs. elite sacks around 15), which isn't what "defense leaders"
    # means to anyone.
    "defense": lambda r: r.sacks,
}


def _defense_score(row: models.PlayerSeasonStats) -> float:
    """DPOY-only composite (see /player-stats/awards): sacks and picks are
    rare, game-defining plays; tackle volume is real but much more common, so
    it's weighted as a tiebreaker rather than the primary signal. Elite
    ranges this is calibrated against: ~15 sacks, ~120-160 tackles, ~5-8 INTs
    in a season. A simple, transparent composite, not an official rating."""
    return (row.sacks or 0) * 4 + (row.def_interceptions or 0) * 5 + (row.combined_tackles or 0) * 0.15


def _row_out(r: models.PlayerSeasonStats) -> dict:
    return {
        "player_id": r.player_id,
        "name": r.name,
        "position": r.position,
        "team": r.team,
        "games": r.games,
        "passing_yards": r.passing_yards,
        "passing_tds": r.passing_tds,
        "interceptions": r.interceptions,
        "rushing_yards": r.rushing_yards,
        "rushing_tds": r.rushing_tds,
        "receptions": r.receptions,
        "receiving_yards": r.receiving_yards,
        "receiving_tds": r.receiving_tds,
        "fantasy_points": r.fantasy_points,
        "fantasy_points_ppr": r.fantasy_points_ppr,
        "sacks": r.sacks,
        "combined_tackles": r.combined_tackles,
        "def_interceptions": r.def_interceptions,
        # Advanced (Pro-Football-Reference) — supplemental, can be null even
        # when the core stat above it is populated.
        "passing_pressure_pct": r.passing_pressure_pct,
        "passing_on_tgt_pct": r.passing_on_tgt_pct,
        "passing_air_yards_per_att": r.passing_air_yards_per_att,
        "rush_yards_before_contact": r.rush_yards_before_contact,
        "rush_yards_after_contact": r.rush_yards_after_contact,
        "rush_broken_tackles": r.rush_broken_tackles,
        "rec_yards_after_catch": r.rec_yards_after_catch,
        "rec_avg_depth_of_target": r.rec_avg_depth_of_target,
        "rec_broken_tackles": r.rec_broken_tackles,
        "rec_drop_pct": r.rec_drop_pct,
    }


def _latest_loaded_season(db: Session) -> int | None:
    return db.query(func.max(models.PlayerSeasonStats.season)).scalar()


def _resolve_season(db: Session, season: int | None) -> int:
    if season is not None:
        return season
    latest = _latest_loaded_season(db)
    if latest is None:
        raise HTTPException(
            status_code=404,
            detail="No player stats loaded yet. Run: python -m app.scripts.load_player_stats",
        )
    return latest


@router.get("/player-stats/seasons")
def available_seasons(db: Session = Depends(get_db)):
    seasons = [s for (s,) in db.query(models.PlayerSeasonStats.season).distinct().order_by(models.PlayerSeasonStats.season.desc())]
    return {"seasons": seasons, "latest": seasons[0] if seasons else None}


@router.get("/player-stats/leaders")
def leaders(
    category: str = Query("overall", pattern="^(overall|passing|rushing|receiving|defense)$"),
    season: int | None = Query(None, description="Defaults to the most recently loaded season"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    season = _resolve_season(db, season)

    query = db.query(models.PlayerSeasonStats).filter(models.PlayerSeasonStats.season == season)
    if category == "passing":
        query = query.filter(models.PlayerSeasonStats.passing_yards.isnot(None))
    elif category == "rushing":
        query = query.filter(models.PlayerSeasonStats.rushing_yards.isnot(None))
    elif category == "receiving":
        query = query.filter(models.PlayerSeasonStats.receiving_yards.isnot(None))
    elif category == "defense":
        query = query.filter(models.PlayerSeasonStats.sacks.isnot(None))
    else:
        query = query.filter(models.PlayerSeasonStats.fantasy_points_ppr.isnot(None))

    rows = query.all()
    key = CATEGORY_SORT[category]
    rows.sort(key=lambda r: key(r) or 0, reverse=True)

    return {"season": season, "category": category, "players": [_row_out(r) for r in rows[:limit]]}


@router.get("/player-stats/awards")
def awards(season: int | None = Query(None), db: Session = Depends(get_db)):
    """Top-5 stats-based candidates for MVP, OPOY, and DPOY. Not betting odds
    and not a prediction of actual voting — see `methodology`."""
    season = _resolve_season(db, season)
    rows = db.query(models.PlayerSeasonStats).filter(models.PlayerSeasonStats.season == season).all()

    mvp = sorted(
        (r for r in rows if r.position == "QB" and r.fantasy_points is not None),
        key=lambda r: r.fantasy_points,
        reverse=True,
    )[:5]
    opoy = sorted(
        (r for r in rows if r.position in ("RB", "WR", "TE") and r.fantasy_points_ppr is not None),
        key=lambda r: r.fantasy_points_ppr,
        reverse=True,
    )[:5]
    dpoy = sorted(
        (r for r in rows if r.sacks is not None),
        key=_defense_score,
        reverse=True,
    )[:5]

    return {
        "season": season,
        "methodology": {
            "mvp": "Quarterbacks ranked by standard fantasy points (passing + rushing production). "
            "Real MVP voting weights team success and narrative too, so this is a statistical proxy, not a prediction.",
            "opoy": "Running backs, wide receivers, and tight ends ranked by PPR fantasy points.",
            "dpoy": "Defenders ranked by a simple composite: (sacks x4) + (interceptions x5) + (combined tackles x0.15).",
        },
        "mvp": [_row_out(r) for r in mvp],
        "opoy": [_row_out(r) for r in opoy],
        "dpoy": [_row_out(r) for r in dpoy],
    }
