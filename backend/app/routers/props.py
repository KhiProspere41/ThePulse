"""NFL player props.

Unlike game lines, props are fetched on demand rather than polled: The Odds
API bills them per market per event, so a single 16-game slate across six
markets costs roughly a fifth of the free tier's monthly allowance. A request
here serves whatever is cached and only spends credits when the cache is stale
(or `refresh=true` is passed explicitly).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.ingest import ingest_player_props, latest_player_props
from app.odds_api import player_prop_markets
from app.probability import american_to_implied_prob

router = APIRouter(tags=["props"])

# Human-readable labels for the market keys, used by the UI's market tabs.
MARKET_LABELS = {
    "player_pass_yds": "Passing Yards",
    "player_pass_tds": "Passing TDs",
    "player_rush_yds": "Rushing Yards",
    "player_reception_yds": "Receiving Yards",
    "player_receptions": "Receptions",
    "player_anytime_td": "Anytime TD",
}


@router.get("/props/markets")
def prop_markets():
    """The prop markets this deployment is configured to pull, with labels."""
    return [{"key": key, "label": MARKET_LABELS.get(key, key)} for key in player_prop_markets()]


@router.get("/props/{game_id}", response_model=schemas.PlayerPropsOut)
def get_props(
    game_id: str,
    refresh: bool = Query(False, description="Force a refetch, spending API credits"),
    db: Session = Depends(get_db),
):
    game = db.get(models.Game, game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    result = ingest_player_props(db, game_id, force=refresh)

    snapshots = latest_player_props(db, game_id)
    props = [
        schemas.PlayerPropOut.model_validate(s).model_copy(
            update={"implied_prob": round(american_to_implied_prob(s.price), 4)}
        )
        for s in snapshots
    ]
    props.sort(key=lambda p: (p.market, p.player, p.bookmaker, p.side))

    detail = None
    if result["status"] == "quota_guard":
        detail = (
            "Monthly Odds API allowance is nearly used up, so props were not refreshed. "
            "Showing the last cached prices."
        )
    elif result["status"] == "error":
        detail = f"Could not refresh props ({result.get('error')}). Showing the last cached prices."
    elif result["status"] == "unsupported_league":
        detail = "Player props are only wired up for the NFL."
    elif not props:
        detail = "No player props posted for this game yet."

    return schemas.PlayerPropsOut(
        game=schemas.GameOut.model_validate(game),
        props=props,
        markets=sorted({p.market for p in props}),
        status=result["status"],
        fetched_at=result.get("fetched_at"),
        stale=result["status"] in ("quota_guard", "error"),
        detail=detail,
    )
