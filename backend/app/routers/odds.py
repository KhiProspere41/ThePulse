from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.probability import american_to_implied_prob

router = APIRouter(tags=["odds"])


@router.get("/odds", response_model=list[schemas.GameWithOddsOut])
def get_odds(
    week: int | None = Query(None, description="NFL/CFB week number"),
    league: str = Query("nfl", pattern="^(nfl|college)$"),
    db: Session = Depends(get_db),
):
    query = db.query(models.Game).filter(models.Game.league == league)
    if week is not None:
        query = query.filter(models.Game.week == week)
    games = query.order_by(models.Game.commence_time).all()

    results = []
    for game in games:
        latest_by_key: dict[tuple, models.OddsSnapshot] = {}
        for snap in sorted(game.odds_snapshots, key=lambda s: s.fetched_at, reverse=True):
            key = (snap.bookmaker, snap.market, snap.side)
            latest_by_key.setdefault(key, snap)

        odds_out = []
        for snap in latest_by_key.values():
            odds_out.append(
                schemas.OddsSnapshotOut.model_validate(snap).model_copy(
                    update={"implied_prob": round(american_to_implied_prob(snap.price), 4)}
                )
            )

        game_out = schemas.GameWithOddsOut.model_validate(game).model_copy(update={"odds": odds_out})
        results.append(game_out)

    return results


@router.get("/games/{game_id}", response_model=schemas.GameWithOddsOut)
def get_game(game_id: str, db: Session = Depends(get_db)):
    game = db.get(models.Game, game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    latest_by_key: dict[tuple, models.OddsSnapshot] = {}
    for snap in sorted(game.odds_snapshots, key=lambda s: s.fetched_at, reverse=True):
        key = (snap.bookmaker, snap.market, snap.side)
        latest_by_key.setdefault(key, snap)

    odds_out = [
        schemas.OddsSnapshotOut.model_validate(s).model_copy(
            update={"implied_prob": round(american_to_implied_prob(s.price), 4)}
        )
        for s in latest_by_key.values()
    ]
    return schemas.GameWithOddsOut.model_validate(game).model_copy(update={"odds": odds_out})
