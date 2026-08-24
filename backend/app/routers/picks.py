from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.ingest import update_closing_lines_and_clv

router = APIRouter(tags=["picks"])


BET_TYPES = ("game", "player_prop", "futures")


@router.post("/picks", response_model=schemas.PickOut, status_code=201)
def create_pick(pick_in: schemas.PickCreate, db: Session = Depends(get_db)):
    if pick_in.bet_type not in BET_TYPES:
        raise HTTPException(status_code=400, detail=f"bet_type must be one of {'|'.join(BET_TYPES)}")

    # Futures ("win the Super Bowl") attach to a season, not a game; everything
    # else must point at a real game.
    if pick_in.bet_type == "futures":
        if pick_in.game_id is not None:
            raise HTTPException(status_code=400, detail="Futures picks must not reference a game")
    else:
        if pick_in.game_id is None:
            raise HTTPException(status_code=400, detail="game_id is required for this bet type")
        if db.get(models.Game, pick_in.game_id) is None:
            raise HTTPException(status_code=404, detail="Game not found")

    if pick_in.bet_type == "player_prop" and not pick_in.player:
        raise HTTPException(status_code=400, detail="player is required for a player prop pick")

    pick = models.Pick(**pick_in.model_dump())
    db.add(pick)
    db.commit()
    db.refresh(pick)
    return pick


@router.get("/picks", response_model=list[schemas.PickOut])
def list_picks(
    bet_type: str | None = Query(None, description="game | player_prop | futures"),
    db: Session = Depends(get_db),
):
    """Saved picks, including CLV for any whose game has kicked off."""
    update_closing_lines_and_clv(db)
    query = db.query(models.Pick)
    if bet_type is not None:
        query = query.filter(models.Pick.bet_type == bet_type)
    return query.order_by(models.Pick.entry_time.desc()).all()


@router.patch("/picks/{pick_id}/result", response_model=schemas.PickOut)
def set_pick_result(pick_id: int, result: str, db: Session = Depends(get_db)):
    if result not in ("win", "loss", "push", "pending"):
        raise HTTPException(status_code=400, detail="result must be one of win|loss|push|pending")
    pick = db.get(models.Pick, pick_id)
    if pick is None:
        raise HTTPException(status_code=404, detail="Pick not found")
    pick.result = result
    db.commit()
    db.refresh(pick)
    return pick


@router.delete("/picks/{pick_id}", status_code=204)
def delete_pick(pick_id: int, db: Session = Depends(get_db)):
    """Remove a standalone pick or one leg of a straight slip.

    A parlay leg can't be removed on its own — it would leave the slip's
    stored combined_price describing legs that no longer all exist. Delete
    the whole parlay via DELETE /slips/{id} instead.
    """
    pick = db.get(models.Pick, pick_id)
    if pick is None:
        raise HTTPException(status_code=404, detail="Pick not found")
    if pick.slip is not None and pick.slip.mode == "parlay":
        raise HTTPException(status_code=400, detail="Can't remove one leg of a parlay — delete the whole slip")

    slip = pick.slip
    was_only_leg = slip is not None and len(slip.legs) == 1
    db.delete(pick)
    if was_only_leg:
        db.delete(slip)
    db.commit()
