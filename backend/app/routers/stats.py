from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.ingest import update_closing_lines_and_clv

router = APIRouter(tags=["stats"])


def _profit(stake: float, price: int) -> float:
    return stake * price / 100 if price > 0 else stake * 100 / -price


@router.get("/stats/dashboard")
def dashboard(db: Session = Depends(get_db)):
    """Win rate, ROI, and CLV trend across all settled picks."""
    update_closing_lines_and_clv(db)
    picks = db.query(models.Pick).order_by(models.Pick.entry_time).all()

    settled = [p for p in picks if p.result in ("win", "loss", "push")]
    wins = sum(1 for p in settled if p.result == "win")
    losses = sum(1 for p in settled if p.result == "loss")
    decided = wins + losses

    total_staked = sum(p.stake for p in settled)
    total_profit = 0.0
    for p in settled:
        if p.result == "win":
            total_profit += _profit(p.stake, p.entry_price)
        elif p.result == "loss":
            total_profit -= p.stake

    clv_values = [p.clv for p in picks if p.clv is not None]

    return {
        "total_picks": len(picks),
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
