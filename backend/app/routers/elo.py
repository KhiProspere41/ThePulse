from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.scripts.compute_elo import find_value_games

router = APIRouter(tags=["elo"])


@router.get("/elo/ratings")
def elo_ratings(db: Session = Depends(get_db)):
    rows = db.query(models.TeamElo).filter_by(league="nfl").order_by(models.TeamElo.rating.desc()).all()
    return [{"team": r.team, "rating": round(r.rating, 1)} for r in rows]


@router.get("/elo/value")
def elo_value():
    """Upcoming games where the Elo model's win probability diverges from the
    vig-free market probability — potential value bets."""
    return find_value_games()
