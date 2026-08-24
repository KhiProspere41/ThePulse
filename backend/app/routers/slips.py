"""Bet slips: one or more picks placed together.

Straight mode is a lightweight grouping — each leg is saved and graded
exactly like a standalone pick (POST /picks still works for a single bet on
its own; this is for placing several at once). Parlay mode combines every
leg into one bet: one stake, one combined price, one result that depends on
every leg hitting.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.ingest import update_closing_lines_and_clv
from app.probability import parlay_combined_price
from app.slips import parlay_result

router = APIRouter(tags=["slips"])

BET_TYPES = ("game", "player_prop", "futures")


def _validate_leg(leg: schemas.SlipLegCreate, db: Session) -> None:
    if leg.bet_type not in BET_TYPES:
        raise HTTPException(status_code=400, detail=f"bet_type must be one of {'|'.join(BET_TYPES)}")

    if leg.bet_type == "futures":
        if leg.game_id is not None:
            raise HTTPException(status_code=400, detail="Futures picks must not reference a game")
    else:
        if leg.game_id is None:
            raise HTTPException(status_code=400, detail="game_id is required for this bet type")
        if db.get(models.Game, leg.game_id) is None:
            raise HTTPException(status_code=404, detail=f"Game not found: {leg.game_id}")

    if leg.bet_type == "player_prop" and not leg.player:
        raise HTTPException(status_code=400, detail="player is required for a player prop pick")


def _slip_out(slip: models.Slip) -> schemas.SlipOut:
    return schemas.SlipOut(
        id=slip.id,
        mode=slip.mode,
        created_at=slip.created_at,
        stake=slip.stake,
        combined_price=slip.combined_price,
        result=parlay_result(slip.legs) if slip.mode == "parlay" else "n/a",
        legs=[schemas.PickOut.model_validate(leg) for leg in slip.legs],
    )


@router.post("/slips", response_model=schemas.SlipOut, status_code=201)
def create_slip(slip_in: schemas.SlipCreate, db: Session = Depends(get_db)):
    if slip_in.mode not in ("straight", "parlay"):
        raise HTTPException(status_code=400, detail="mode must be 'straight' or 'parlay'")
    if not slip_in.legs:
        raise HTTPException(status_code=400, detail="A slip needs at least one leg")
    if slip_in.mode == "parlay":
        if len(slip_in.legs) < 2:
            raise HTTPException(status_code=400, detail="A parlay needs at least 2 legs")
        if not slip_in.stake or slip_in.stake <= 0:
            raise HTTPException(status_code=400, detail="A parlay needs a stake")

    for leg in slip_in.legs:
        _validate_leg(leg, db)

    combined_price = (
        parlay_combined_price([leg.entry_price for leg in slip_in.legs]) if slip_in.mode == "parlay" else None
    )

    slip = models.Slip(
        mode=slip_in.mode,
        stake=slip_in.stake if slip_in.mode == "parlay" else None,
        combined_price=combined_price,
    )
    db.add(slip)
    db.flush()  # assigns slip.id, needed before the legs can reference it

    for leg in slip_in.legs:
        db.add(
            models.Pick(
                game_id=leg.game_id,
                bet_type=leg.bet_type,
                market=leg.market,
                selection=leg.selection,
                player=leg.player,
                point=leg.point,
                entry_price=leg.entry_price,
                # A parlay leg isn't independently staked — the slip's stake
                # is what's actually wagered. Zero here keeps it out of the
                # per-pick ROI math in /stats/dashboard without a special case.
                stake=leg.stake if slip_in.mode == "straight" else 0.0,
                slip_id=slip.id,
            )
        )

    db.commit()
    db.refresh(slip)
    return _slip_out(slip)


@router.get("/slips", response_model=list[schemas.SlipOut])
def list_slips(db: Session = Depends(get_db)):
    """Saved slips, newest first, with each leg's CLV backfilled once its game
    has kicked off (same backfill /picks does)."""
    update_closing_lines_and_clv(db)
    slips = db.query(models.Slip).order_by(models.Slip.created_at.desc()).all()
    return [_slip_out(s) for s in slips]


@router.delete("/slips/{slip_id}", status_code=204)
def delete_slip(slip_id: int, db: Session = Depends(get_db)):
    """Remove a slip and all of its legs — the only way to remove a parlay,
    since its legs can't be deleted individually (see DELETE /picks/{id})."""
    slip = db.get(models.Slip, slip_id)
    if slip is None:
        raise HTTPException(status_code=404, detail="Slip not found")
    db.delete(slip)
    db.commit()
