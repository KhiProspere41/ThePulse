"""Monte Carlo season simulation for NFL team futures.

The Odds API publishes exactly one NFL futures feed -- the Super Bowl winner
outrights market. There is no division-winner feed and no season win-total
feed, so those two markets cannot be aggregated; they are modelled here
instead, off the same Elo ratings `app.scripts.compute_elo` already builds
from historical results.

What one iteration does:

  1. Start every team from its completed results this season.
  2. Play out the remaining schedule, deciding each game by the Elo win
     probability (including home-field advantage).
  3. Rank each conference, award division titles, seed the playoffs 1-7.
  4. Play the bracket -- wild card, divisional, conference, Super Bowl.

Aggregating a few thousand of those gives division-title probability, a full
cumulative win-total ladder (P(at least k wins) for every k), playoff odds, and
a model Super Bowl probability that can be priced against the real outrights
market.

Known simplifications, all of which push results toward the middle:

  * Ties are not simulated. NFL ties run well under 1% of games.
  * Standings ties are broken at random per iteration rather than by the real
    NFL tiebreakers (head-to-head, division record, common games, strength of
    victory). Randomising splits the probability evenly among tied teams,
    which is unbiased in aggregate but wrong for any specific matchup.
  * Ratings are frozen at their current values rather than updated game to
    game, so the spread of outcomes is slightly narrower than reality.
  * Injuries, bye weeks and rest are not modelled at all.
"""

import datetime as dt
import logging
import math
import random
from bisect import bisect_left
from collections import OrderedDict, defaultdict

from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.divisions import ALL_TEAMS, CONFERENCES, DIVISIONS, TEAM_TO_CONFERENCE, TEAM_TO_DIVISION, normalize
from app.elo import INITIAL_RATING, expected_score, HOME_FIELD_ADVANTAGE
from app.teams import ODDS_API_NAME_TO_ABBR, to_elo_key

logger = logging.getLogger(__name__)

REGULAR_SEASON_GAMES = 17
PLAYOFF_SEEDS = 7

ABBR_TO_NAME = {abbr: name for name, abbr in ODDS_API_NAME_TO_ABBR.items()}

# In-process cache: the simulation is deterministic given (season, iterations,
# ratings, schedule) and takes a couple of seconds, which is too slow to redo
# on every page load but far too cheap to bother persisting.
#
# Bounded and LRU-evicted on purpose, not just TTL-checked on read: `season`
# and `iterations` reach this from public, unauthenticated query params (see
# routers/futures.py), so an unbounded dict here is a memory-growth vector —
# every distinct combination a caller sends adds a permanent entry otherwise.
_CACHE_MAX_ENTRIES = 16
_cache: "OrderedDict[tuple, tuple[dt.datetime, dict]]" = OrderedDict()


def _cache_get(key: tuple) -> dict | None:
    entry = _cache.get(key)
    if entry is None:
        return None
    _cache.move_to_end(key)
    return entry


def _cache_put(key: tuple, value: dict) -> None:
    _cache[key] = value
    _cache.move_to_end(key)
    while len(_cache) > _CACHE_MAX_ENTRIES:
        _cache.popitem(last=False)


def season_of(commence_time: dt.datetime) -> int:
    """NFL season a kickoff belongs to; seasons straddle New Year."""
    return commence_time.year if commence_time.month >= 3 else commence_time.year - 1


def current_season() -> int:
    """The NFL season currently in progress, anchored on the configured opener."""
    start = settings.nfl_season_start
    now = dt.datetime.utcnow()
    return start.year if now >= start.replace(month=3, day=1) else start.year - 1


# --- inputs ----------------------------------------------------------------


def _load_ratings(db: Session) -> dict[str, float]:
    """Current Elo ratings, keyed by franchise abbreviation.

    Teams with no rating (a franchise that never appeared in the loaded
    history) fall back to the 1500 baseline so the league is always complete.
    """
    ratings: dict[str, float] = {}
    for row in db.query(models.TeamElo).filter_by(league="nfl").all():
        ratings[normalize(to_elo_key(row.team))] = row.rating
    return {team: ratings.get(team, INITIAL_RATING) for team in ALL_TEAMS}


def _load_schedule(db: Session, season: int) -> tuple[list[dict], list[tuple[str, str]], dict[str, list[int]]]:
    """Return (completed, remaining, record) for one season.

    Games arrive from two sources with different naming conventions -- live
    Odds API events use full team names, the nflverse loader uses abbreviations
    -- so everything is normalised to abbreviations and de-duplicated on
    (week, home, away). Live events win ties because they carry the live status.
    """
    seen: dict[tuple, dict] = {}

    # The published schedule is the base layer: every game of the season,
    # including the ones no book has priced yet.
    for row in db.query(models.ScheduledGame).filter(models.ScheduledGame.season == season).all():
        home, away = normalize(row.home_team), normalize(row.away_team)
        if home not in TEAM_TO_DIVISION or away not in TEAM_TO_DIVISION:
            continue
        seen[(row.week, home, away)] = {
            "home": home,
            "away": away,
            "completed": bool(row.completed) and row.home_score is not None and row.away_score is not None,
            "home_score": row.home_score,
            "away_score": row.away_score,
            "source": "schedule",
        }

    # The odds board is overlaid on top: it carries live results, and covers
    # the season on its own if the schedule was never loaded.
    # `Game.season` was only added to the live ingest path later, so rows
    # written by an earlier build can have it NULL. Fall back to deriving the
    # season from kickoff rather than silently dropping those games — a
    # simulation missing half its schedule looks like a modelling bug.
    games = [
        game
        for game in db.query(models.Game)
        .filter(models.Game.league == "nfl")
        .order_by(models.Game.commence_time)
        .all()
        if (game.season if game.season is not None else season_of(game.commence_time)) == season
    ]

    for game in games:
        home = normalize(to_elo_key(game.home_team))
        away = normalize(to_elo_key(game.away_team))
        if home not in TEAM_TO_DIVISION or away not in TEAM_TO_DIVISION:
            continue
        key = (game.week, home, away)
        entry = {
            "home": home,
            "away": away,
            "completed": bool(game.completed) and game.home_score is not None and game.away_score is not None,
            "home_score": game.home_score,
            "away_score": game.away_score,
            "source": game.source,
        }
        prior = seen.get(key)
        if prior is None or (entry["completed"] and not prior["completed"]):
            seen[key] = entry

    completed: list[dict] = []
    remaining: list[tuple[str, str]] = []
    record: dict[str, list[int]] = {team: [0, 0, 0] for team in ALL_TEAMS}  # wins, losses, ties

    for entry in seen.values():
        if entry["completed"]:
            completed.append(entry)
            home, away = entry["home"], entry["away"]
            if entry["home_score"] > entry["away_score"]:
                record[home][0] += 1
                record[away][1] += 1
            elif entry["home_score"] < entry["away_score"]:
                record[away][0] += 1
                record[home][1] += 1
            else:
                record[home][2] += 1
                record[away][2] += 1
        else:
            remaining.append((entry["home"], entry["away"]))

    return completed, remaining, record


def _filler_games(record: dict[str, list[int]], remaining: list[tuple[str, str]]) -> dict[str, int]:
    """How many games each team is short of a full 17-game season.

    Only the current week or two of the schedule is available from the odds
    feed, so without this the win ladder would describe a two-game season. Any
    shortfall is played out against a league-average opponent at a neutral
    site, which is a blunt but unbiased stand-in. Running
    `app.scripts.load_schedule` loads the real schedule and drives this to zero.
    """
    scheduled = defaultdict(int)
    for home, away in remaining:
        scheduled[home] += 1
        scheduled[away] += 1

    filler = {}
    for team in ALL_TEAMS:
        wins, losses, ties = record[team]
        played = wins + losses + ties
        filler[team] = max(0, REGULAR_SEASON_GAMES - played - scheduled[team])
    return filler


# --- the simulation --------------------------------------------------------


def _seed_conference(
    conf_divisions: list[tuple[str, ...]], wins: dict[str, int], rng: random.Random
) -> list[str]:
    """Playoff seeds 1-7 for one conference: four division winners, then the
    three best remaining teams. Ties broken at random (see module docstring)."""
    conf_teams = [team for teams in conf_divisions for team in teams]
    order = sorted(conf_teams, key=lambda t: (-wins[t], rng.random()))
    rank = {team: i for i, team in enumerate(order)}

    division_winners = [min(teams, key=lambda t: rank[t]) for teams in conf_divisions]
    division_winners.sort(key=lambda t: rank[t])

    winners = set(division_winners)
    wildcards = [t for t in order if t not in winners][: PLAYOFF_SEEDS - len(division_winners)]
    return division_winners + wildcards


def _binomial_cdf(n: int, p: float) -> list[float]:
    """Cumulative distribution of wins in `n` independent games at probability
    `p`, for inverse-transform sampling via `bisect_left`."""
    cdf: list[float] = []
    total = 0.0
    for k in range(n + 1):
        total += math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))
        cdf.append(total)
    cdf[-1] = 1.0  # guard against float drift leaving a sliver above the top bin
    return cdf


def _play(home: str, away: str, ratings: dict[str, float], rng: random.Random, neutral: bool = False) -> str:
    hfa = 0.0 if neutral else HOME_FIELD_ADVANTAGE
    p_home = expected_score(ratings[home] + hfa, ratings[away])
    return home if rng.random() < p_home else away


def _play_bracket(seeds: list[str], ratings: dict[str, float], rng: random.Random) -> str:
    """One conference's playoff bracket; returns the conference champion.

    Standard 7-seed format: the 1 seed has a bye, the bracket re-seeds after
    the wild card round so the 1 seed always draws the lowest survivor.
    """
    one, two, three, four, five, six, seven = seeds
    survivors = [one]
    survivors.append(_play(two, seven, ratings, rng))
    survivors.append(_play(three, six, ratings, rng))
    survivors.append(_play(four, five, ratings, rng))

    survivors.sort(key=seeds.index)
    top, second, third, fourth = survivors
    div_a = _play(top, fourth, ratings, rng)
    div_b = _play(second, third, ratings, rng)

    finalists = sorted([div_a, div_b], key=seeds.index)
    return _play(finalists[0], finalists[1], ratings, rng)


def _run(
    ratings: dict[str, float],
    record: dict[str, list[int]],
    remaining: list[tuple[str, str]],
    filler: dict[str, int],
    iterations: int,
    seed: int | None,
) -> dict:
    rng = random.Random(seed)
    league_average = sum(ratings.values()) / len(ratings)

    # Precompute per-game and per-filler win probabilities once; the inner loop
    # then does nothing but compare a random draw against a float.
    scheduled = [(home, away, expected_score(ratings[home] + HOME_FIELD_ADVANTAGE, ratings[away]))
                 for home, away in remaining]
    filler_prob = {team: expected_score(ratings[team], league_average) for team in ALL_TEAMS}

    # Filler games are independent coin flips at a fixed probability, i.e. a
    # binomial draw. Sampling one inverse-CDF lookup per team beats flipping up
    # to seventeen coins per team per iteration by an order of magnitude, and is
    # exactly the same distribution.
    filler_cdf = {
        team: _binomial_cdf(count, filler_prob[team]) for team, count in filler.items() if count
    }

    conferences = {
        conf: [teams for division, teams in DIVISIONS.items() if division.startswith(conf)]
        for conf in CONFERENCES
    }
    base_wins = {team: record[team][0] for team in ALL_TEAMS}

    win_counts: dict[str, list[int]] = {team: [0] * (REGULAR_SEASON_GAMES + 1) for team in ALL_TEAMS}
    division_titles: dict[str, int] = dict.fromkeys(ALL_TEAMS, 0)
    playoff_berths: dict[str, int] = dict.fromkeys(ALL_TEAMS, 0)
    conference_titles: dict[str, int] = dict.fromkeys(ALL_TEAMS, 0)
    championships: dict[str, int] = dict.fromkeys(ALL_TEAMS, 0)

    random_ = rng.random
    for _ in range(iterations):
        wins = dict(base_wins)

        for home, away, p_home in scheduled:
            if random_() < p_home:
                wins[home] += 1
            else:
                wins[away] += 1

        for team, cdf in filler_cdf.items():
            wins[team] += bisect_left(cdf, random_())

        for team, total in wins.items():
            win_counts[team][min(total, REGULAR_SEASON_GAMES)] += 1

        champions = []
        for conf_divisions in conferences.values():
            seeds = _seed_conference(conf_divisions, wins, rng)
            for team in seeds[:4]:
                division_titles[team] += 1
            for team in seeds:
                playoff_berths[team] += 1
            champion = _play_bracket(seeds, ratings, rng)
            conference_titles[champion] += 1
            champions.append(champion)

        winner = _play(champions[0], champions[1], ratings, rng, neutral=True)
        championships[winner] += 1

    return {
        "win_counts": win_counts,
        "division_titles": division_titles,
        "playoff_berths": playoff_berths,
        "conference_titles": conference_titles,
        "championships": championships,
    }


# --- public API ------------------------------------------------------------


def simulate_season(
    db: Session,
    season: int | None = None,
    iterations: int | None = None,
    seed: int | None = None,
    refresh: bool = False,
) -> dict:
    """Run (or serve from cache) a full-season simulation.

    `iterations` and `seed` are deliberately not settable from the public API
    (see routers/futures.py) — this signature keeps them for scripts/tests,
    but the clamp below is a backstop, not the primary control. A single
    100k-iteration run measured ~23s of wall time; letting an unauthenticated
    caller pick both `iterations` and an arbitrary `seed` turned that into an
    unbounded-cost, cache-defeating DoS. `settings.sim_max_iterations` is the
    real ceiling for anything reachable from a request.
    """
    season = season or current_season()
    iterations = max(200, min(iterations or settings.sim_iterations, settings.sim_max_iterations))

    cache_key = (season, iterations, seed)
    cached = _cache_get(cache_key)
    if cached and not refresh:
        generated_at, payload = cached
        if dt.datetime.utcnow() - generated_at < dt.timedelta(minutes=settings.sim_cache_minutes):
            return payload

    ratings = _load_ratings(db)
    rated_teams = {normalize(to_elo_key(r.team)) for r in db.query(models.TeamElo).filter_by(league="nfl").all()}
    completed, remaining, record = _load_schedule(db, season)
    filler = _filler_games(record, remaining)

    started = dt.datetime.utcnow()
    totals = _run(ratings, record, remaining, filler, iterations, seed)
    elapsed = (dt.datetime.utcnow() - started).total_seconds()

    thresholds = list(range(1, REGULAR_SEASON_GAMES + 1))
    teams_out = []
    for team in ALL_TEAMS:
        counts = totals["win_counts"][team]
        distribution = {str(k): round(counts[k] / iterations, 4) for k in range(REGULAR_SEASON_GAMES + 1)}
        # Cumulative from the top so P(at least k) is exact rather than 1 - CDF.
        at_least: dict[str, float] = {}
        running = 0
        for k in range(REGULAR_SEASON_GAMES, 0, -1):
            running += counts[k]
            at_least[str(k)] = round(running / iterations, 4)
        mean_wins = sum(k * counts[k] for k in range(REGULAR_SEASON_GAMES + 1)) / iterations

        wins, losses, ties = record[team]
        teams_out.append(
            {
                "team": team,
                "name": ABBR_TO_NAME.get(team, team),
                "conference": TEAM_TO_CONFERENCE[team],
                "division": TEAM_TO_DIVISION[team],
                "elo": round(ratings[team], 1),
                "record": {"wins": wins, "losses": losses, "ties": ties},
                "mean_wins": round(mean_wins, 2),
                "win_distribution": distribution,
                "win_at_least": at_least,
                "division_title_prob": round(totals["division_titles"][team] / iterations, 4),
                "playoff_prob": round(totals["playoff_berths"][team] / iterations, 4),
                "conference_title_prob": round(totals["conference_titles"][team] / iterations, 4),
                "super_bowl_prob": round(totals["championships"][team] / iterations, 4),
            }
        )

    teams_out.sort(key=lambda t: t["super_bowl_prob"], reverse=True)

    payload = {
        "season": season,
        "iterations": iterations,
        "seed": seed,
        "generated_at": started.isoformat(),
        "elapsed_seconds": round(elapsed, 2),
        "win_thresholds": thresholds,
        "schedule": {
            "games_completed": len(completed),
            "games_remaining": len(remaining),
            "games_known": len(completed) + len(remaining),
            "games_expected": REGULAR_SEASON_GAMES * len(ALL_TEAMS) // 2,
            "complete": not any(filler.values()),
            "filler_games_per_team": {t: n for t, n in sorted(filler.items()) if n},
        },
        "elo": {
            "teams_rated": len(rated_teams & set(ALL_TEAMS)),
            "unrated_teams": sorted(set(ALL_TEAMS) - rated_teams),
        },
        "teams": teams_out,
    }

    _cache_put(cache_key, (dt.datetime.utcnow(), payload))
    logger.info(
        "Simulated season %s: %d iterations over %d remaining games in %.2fs",
        season, iterations, len(remaining), elapsed,
    )
    return payload
