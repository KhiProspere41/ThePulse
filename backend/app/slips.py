"""Parlay grading — shared between routers/slips.py (display) and
routers/stats.py (ROI), so there's exactly one definition of what a parlay's
overall result is.
"""

from app import models


def parlay_result(legs: list["models.Pick"]) -> str:
    """A parlay wins only if every leg wins. One loss loses the whole thing.
    All-push is a push. A mix of wins and pushes still wins — real
    sportsbooks recompute the payout with pushed legs removed rather than
    voiding it, which this doesn't model; it's a simplification, not a bug,
    same spirit as the "ties broken at random" caveat on the Elo model.
    """
    if not legs:
        return "pending"
    results = [leg.result for leg in legs]
    if any(r == "loss" for r in results):
        return "loss"
    if any(r == "pending" for r in results):
        return "pending"
    if all(r == "push" for r in results):
        return "push"
    return "win"
