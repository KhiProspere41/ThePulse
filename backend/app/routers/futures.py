"""NFL team futures: the real Super Bowl outrights market, plus the
division-title and season-win-total markets that no feed provides.

The Odds API's only NFL futures sport key is
`americanfootball_nfl_super_bowl_winner`. Division winners and season win
totals are modelled by `app.simulate` off the project's own Elo ratings, which
also yields a model Super Bowl probability to price against the live market.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import schemas
from app.config import settings
from app.database import get_db
from app.divisions import DIVISIONS
from app.ingest import ingest_futures, latest_futures
from app.probability import american_to_implied_prob
from app.simulate import simulate_season
from app.teams import to_elo_key

router = APIRouter(tags=["futures"])


def _american_to_payout(price: int) -> float:
    """Profit per unit staked at American odds."""
    return price / 100 if price > 0 else 100 / -price


def _devigged_market(prices: list) -> dict[str, dict]:
    """Collapse every book's outrights board into one fair probability per team.

    A Super Bowl board carries enormous hold — the raw implied probabilities
    across 32 teams routinely sum to 1.3 or more — so comparing a model number
    against a raw implied price would flag "value" on literally every team.
    Each bookmaker's board is normalised to sum to 1 first, then averaged
    across books. The best available price is tracked separately, since that's
    what you'd actually bet into.
    """
    by_book: dict[str, dict[str, float]] = {}
    best: dict[str, tuple[int, str]] = {}

    for snap in prices:
        by_book.setdefault(snap.bookmaker, {})[snap.team] = american_to_implied_prob(snap.price)
        current = best.get(snap.team)
        if current is None or snap.price > current[0]:
            best[snap.team] = (snap.price, snap.bookmaker)

    fair_totals: dict[str, list[float]] = {}
    for board in by_book.values():
        overround = sum(board.values())
        if overround <= 0:
            continue
        for team, prob in board.items():
            fair_totals.setdefault(team, []).append(prob / overround)

    out: dict[str, dict] = {}
    for team, probs in fair_totals.items():
        price, book = best.get(team, (None, None))
        out[team] = {
            "market_fair_prob": round(sum(probs) / len(probs), 4),
            "best_price": price,
            "best_book": book,
            "books": len(probs),
        }
    return out


@router.get("/futures/super-bowl", response_model=schemas.FuturesOut)
def super_bowl_futures(
    refresh: bool = Query(False, description="Force a refetch, spending one API credit"),
    db: Session = Depends(get_db),
):
    """Raw Super Bowl winner prices from every book, newest snapshot per team."""
    result = ingest_futures(db, force=refresh)
    snapshots = latest_futures(db)

    prices = [
        schemas.FuturesPriceOut.model_validate(s).model_copy(
            update={"implied_prob": round(american_to_implied_prob(s.price), 4)}
        )
        for s in snapshots
    ]
    prices.sort(key=lambda p: -p.price if p.price < 0 else p.price)

    detail = None
    if result["status"] == "quota_guard":
        detail = "Monthly Odds API allowance is nearly used up — showing the last cached prices."
    elif result["status"] == "error":
        detail = f"Could not refresh futures ({result.get('error')}). Showing the last cached prices."
    elif not prices:
        detail = "No Super Bowl prices cached yet. Set ODDS_API_KEY and refresh."

    return schemas.FuturesOut(
        sport_key=settings.nfl_futures_sport_key,
        prices=prices,
        status=result["status"],
        fetched_at=max((s.fetched_at for s in snapshots), default=None),
        detail=detail,
    )


@router.get("/futures/simulation")
def futures_simulation(
    season: int | None = Query(None, description="Defaults to the season in progress"),
    refresh: bool = Query(False, description="Bypass the simulation cache"),
    db: Session = Depends(get_db),
):
    """Model probabilities for division titles, season win totals, playoff
    berths and the Super Bowl, from a Monte Carlo run over the Elo ratings.

    Iteration count and RNG seed are fixed server-side (`settings.sim_iterations`),
    not caller-supplied: a 100k-iteration run measured ~23s of wall time, and an
    arbitrary seed defeats the cache on every request. Letting an unauthenticated
    caller control both is an easy denial-of-service, not a real feature — nothing
    in the UI ever needs a specific seed or a non-default iteration count.
    """
    return simulate_season(db, season=season, refresh=refresh)


@router.get("/futures/board")
def futures_board(
    refresh: bool = Query(False),
    db: Session = Depends(get_db),
):
    """One row per team combining everything: Elo, projected record, division
    and win-total probabilities, and the model's Super Bowl number against the
    market's devigged fair price plus the best available payout."""
    sim = simulate_season(db, refresh=refresh)
    market = _devigged_market(latest_futures(db))

    rows = []
    for team in sim["teams"]:
        # The books publish full team names; the model is keyed by abbreviation.
        quote = next(
            (v for name, v in market.items() if to_elo_key(name) == team["team"]),
            None,
        )
        row = {**team, "market": quote}
        if quote and quote["best_price"] is not None:
            model_prob = team["super_bowl_prob"]
            payout = _american_to_payout(quote["best_price"])
            row["edge"] = round(model_prob - quote["market_fair_prob"], 4)
            # Expected profit per unit staked at the best available price, using
            # the model's probability. Positive means the model thinks the price
            # is too long.
            row["ev_per_unit"] = round(model_prob * payout - (1 - model_prob), 4)
        else:
            row["edge"] = None
            row["ev_per_unit"] = None
        rows.append(row)

    return {
        "season": sim["season"],
        "iterations": sim["iterations"],
        "generated_at": sim["generated_at"],
        "schedule": sim["schedule"],
        "elo": sim["elo"],
        "win_thresholds": sim["win_thresholds"],
        "divisions": list(DIVISIONS),
        "market_books": sorted({s.bookmaker for s in latest_futures(db)}),
        "teams": rows,
    }


@router.get("/futures/divisions")
def division_races(db: Session = Depends(get_db)):
    """Division-title probabilities grouped by division, longest odds last."""
    sim = simulate_season(db)
    by_division: dict[str, list[dict]] = {name: [] for name in DIVISIONS}
    for team in sim["teams"]:
        by_division[team["division"]].append(
            {
                "team": team["team"],
                "name": team["name"],
                "elo": team["elo"],
                "record": team["record"],
                "mean_wins": team["mean_wins"],
                "division_title_prob": team["division_title_prob"],
                "playoff_prob": team["playoff_prob"],
            }
        )
    for teams in by_division.values():
        teams.sort(key=lambda t: t["division_title_prob"], reverse=True)

    return {
        "season": sim["season"],
        "iterations": sim["iterations"],
        "generated_at": sim["generated_at"],
        "schedule": sim["schedule"],
        "divisions": by_division,
    }

