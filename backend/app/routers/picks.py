from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.ingest import update_closing_lines_and_clv

router = APIRouter(tags=["picks"])


@router.post("/picks", response_model=schemas.PickOut, status_code=201)
def create_pick(pick_in: schemas.PickCreate, db: Session = Depends(get_db)):
    game = db.get(models.Game, pick_in.game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    pick = models.Pick(**pick_in.model_dump())
    db.add(pick)
    db.commit()
    db.refresh(pick)
    return pick


@router.get("/picks", response_model=list[schemas.PickOut])
def list_picks(db: Session = Depends(get_db)):
    """Saved picks, including CLV for any whose game has kicked off."""
    update_closing_lines_and_clv(db)
    return db.query(models.Pick).order_by(models.Pick.entry_time.desc()).all()


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
