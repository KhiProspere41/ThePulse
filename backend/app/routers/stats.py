from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.ingest import update_closing_lines_and_clv
from app.slips import parlay_result

router = APIRouter(tags=["stats"])


def _profit(stake: float, price: int) -> float:
    return stake * price / 100 if price > 0 else stake * 100 / -price


@router.get("/stats/dashboard")
def dashboard(db: Session = Depends(get_db)):
    """Win rate, ROI, and CLV trend across all settled bets.

    A "bet" here is a standalone pick, a straight-slip leg (each staked and
    graded independently, same as a standalone pick), or one parlay slip
    (its own stake and combined price, at the slip level) — never a parlay
    leg on its own, which would count one wager as several.
    """
    update_closing_lines_and_clv(db)
    picks = db.query(models.Pick).order_by(models.Pick.entry_time).all()
    parlays = db.query(models.Slip).filter(models.Slip.mode == "parlay").all()
    parlay_leg_ids = {leg.id for slip in parlays for leg in slip.legs}

    bets = [
        {"stake": p.stake, "price": p.entry_price, "result": p.result}
        for p in picks
        if p.id not in parlay_leg_ids
    ] + [
        {"stake": s.stake, "price": s.combined_price, "result": parlay_result(s.legs)}
        for s in parlays
        if s.stake and s.combined_price
    ]

    settled = [b for b in bets if b["result"] in ("win", "loss", "push")]
    wins = sum(1 for b in settled if b["result"] == "win")
    losses = sum(1 for b in settled if b["result"] == "loss")
    decided = wins + losses

    total_staked = sum(b["stake"] for b in settled)
    total_profit = 0.0
    for b in settled:
        if b["result"] == "win":
            total_profit += _profit(b["stake"], b["price"])
        elif b["result"] == "loss":
            total_profit -= b["stake"]

    clv_values = [p.clv for p in picks if p.clv is not None]

    return {
        "total_picks": len(bets),
        "settled_picks": len(settled),
        "win_rate": round(wins / decided, 4) if decided else None,
        "roi": round(total_profit / total_staked, 4) if total_staked else None,
        "total_profit_units": round(total_profit, 2),
        "avg_clv": round(sum(clv_values) / len(clv_values), 2) if clv_values else None,
        "clv_trend": [
            {"pick_id": p.id, "entry_time": p.entry_time, "clv": p.clv}
            for p in picks
            if p.clv is not None
        ],
    }


@router.get("/stats/api-usage", response_model=schemas.ApiUsageOut)
def api_usage(db: Session = Depends(get_db)):
    """How much of the Odds API's monthly allowance is left.

    Surfaced in the UI because the free tier is 500 requests/month and player
    props are billed per market per event — it's the number that decides
    whether the app still works at the end of the month."""
    row = db.get(models.ApiUsage, 1)
    return row or models.ApiUsage(id=1)
