from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.probability import american_to_implied_prob

router = APIRouter(tags=["lines"])


@router.get("/lines", response_model=schemas.LinesOut)
def get_lines(game: str = Query(..., description="Game ID"), db: Session = Depends(get_db)):
    """Spread / moneyline / total for a specific game, grouped by sportsbook so
    they can be compared side-by-side."""
    game_row = db.get(models.Game, game)
    if game_row is None:
        raise HTTPException(status_code=404, detail="Game not found")

    latest_by_key: dict[tuple, models.OddsSnapshot] = {}
    for snap in sorted(game_row.odds_snapshots, key=lambda s: s.fetched_at, reverse=True):
        key = (snap.bookmaker, snap.market, snap.side)
        latest_by_key.setdefault(key, snap)

    by_bookmaker: dict[str, list[schemas.OddsSnapshotOut]] = {}
    for snap in latest_by_key.values():
        out = schemas.OddsSnapshotOut.model_validate(snap).model_copy(
            update={"implied_prob": round(american_to_implied_prob(snap.price), 4)}
        )
        by_bookmaker.setdefault(snap.bookmaker, []).append(out)

    return schemas.LinesOut(game=schemas.GameOut.model_validate(game_row), bookmakers=by_bookmaker)
