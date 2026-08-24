"""Loads real NFL player season stats — offense (passing/rushing/receiving)
and defense (sacks/tackles/INTs) — into player_season_stats, for the season
stat leaderboards and the MVP/OPOY/DPOY model.

    python -m app.scripts.load_player_stats --season 2024
    python -m app.scripts.load_player_stats            # most recent season available

Sourced from nflverse's published data via nfl-data-py:
  - Offense: `player_stats_{season}.parquet` (import_seasonal_data)
  - Defense: Pro-Football-Reference's seasonal advanced stats (import_seasonal_pfr)
  - Names/positions/teams: the seasonal roster (import_seasonal_rosters)

nflverse publishes each season's file only after enough of it exists to be
useful (previous seasons appear within days of the season ending; the file
for a season in progress does not exist until nflverse cuts a release). This
script fails loudly and specifically on a missing season rather than a bare
traceback, since "the file isn't out yet" is an expected, recoverable state,
not a bug.
"""

import argparse
import logging
import os

os.environ.setdefault("SSL_CERT_FILE", __import__("certifi").where())

import nfl_data_py as nfl  # noqa: E402 — SSL_CERT_FILE must be set before this import's first network call
import pandas as pd  # noqa: E402
from urllib.error import HTTPError  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# An offensive/special-teams player shows up in the PFR "defensive" file too
# (e.g. a trick-play completion allowed, a punter's stats), which is noise for
# a defense leaderboard — excluded by name rather than an inclusion list,
# because PFR prefixes many real defensive positions with a side ("RDE",
# "LLB", "LCB" for right defensive end / left linebacker / left cornerback),
# and an inclusion list silently drops every one of those. Confirmed this the
# hard way: the actual #1 and #2 NFL sack leaders that season (both listed as
# "RDE"/"LLB") were missing entirely from the first version of this filter.
NON_DEFENSIVE_POSITIONS = {"C", "FB", "FB/DL", "K", "LG", "LT", "OG", "OL", "OT", "P", "QB", "RB", "TE", "WR"}


def _latest_available_season(start: int) -> int | None:
    """Walk backward from `start` to find a season nflverse has actually
    published player_stats for, rather than guessing and failing."""
    import httpx

    with httpx.Client(timeout=10.0) as client:
        for year in range(start, start - 5, -1):
            url = f"https://github.com/nflverse/nflverse-data/releases/download/player_stats/player_stats_{year}.parquet"
            if client.head(url, follow_redirects=True).status_code == 200:
                return year
    return None


def _latest_roster_per_player(rosters: pd.DataFrame) -> pd.DataFrame:
    """Roster rows are weekly snapshots even in the "seasonal" pull — keep
    each player's most recent entry so a mid-season trade lands on their
    final team, not their first."""
    return rosters.sort_values("week").drop_duplicates("player_id", keep="last")


def load_season(season: int) -> int:
    init_db()

    logger.info("Fetching offense stats for %d", season)
    offense = nfl.import_seasonal_data([season], s_type="REG")

    logger.info("Fetching rosters for %d", season)
    rosters = _latest_roster_per_player(nfl.import_seasonal_rosters([season]))
    name_by_id = rosters.set_index("player_id")[["player_name", "position", "team"]]
    pfr_to_gsis = rosters.dropna(subset=["pfr_id"]).set_index("pfr_id")["player_id"].to_dict()

    logger.info("Fetching defensive stats for %d", season)
    try:
        defense = nfl.import_seasonal_pfr("def", [season])
    except (HTTPError, Exception) as exc:  # nflverse's PFR mirror can lag behind the main release
        logger.warning("No defensive stats available for %d yet (%s) — offense only.", season, exc)
        defense = pd.DataFrame()

    db = SessionLocal()
    written = 0
    # Tracks rows created in *this* run — deliberately not relying on
    # db.get() to see a just-added, not-yet-flushed object back: offense and
    # defense can resolve to the same player_id (some defenders show up in
    # both files), and this session never flushes until the final commit.
    pending: dict[tuple[str, int], models.PlayerSeasonStats] = {}
    try:
        for row in offense.itertuples():
            player_id = row.player_id
            meta = name_by_id.loc[player_id] if player_id in name_by_id.index else None

            record = pending.get((player_id, season)) or db.get(models.PlayerSeasonStats, {"player_id": player_id, "season": season})
            if record is None:
                record = models.PlayerSeasonStats(player_id=player_id, season=season)
                db.add(record)
                pending[(player_id, season)] = record

            record.name = meta["player_name"] if meta is not None else player_id
            record.position = meta["position"] if meta is not None else None
            record.team = meta["team"] if meta is not None else None
            record.games = int(row.games) if pd.notna(row.games) else None
            record.completions = int(row.completions)
            record.attempts = int(row.attempts)
            record.passing_yards = float(row.passing_yards)
            record.passing_tds = int(row.passing_tds)
            record.interceptions = int(row.interceptions)
            record.carries = int(row.carries)
            record.rushing_yards = float(row.rushing_yards)
            record.rushing_tds = int(row.rushing_tds)
            record.receptions = int(row.receptions)
            record.targets = int(row.targets)
            record.receiving_yards = float(row.receiving_yards)
            record.receiving_tds = int(row.receiving_tds)
            record.fantasy_points = float(row.fantasy_points)
            record.fantasy_points_ppr = float(row.fantasy_points_ppr)
            written += 1

        # A defender traded mid-season gets THREE PFR rows: one per team stint,
        # PLUS a "2TM"/"3TM" row that is already the combined season total.
        # Summing every row (an earlier version of this script did) double-
        # or triple-counts that player's season — caught this concretely: it
        # put a cornerback at 232 combined tackles for the year, which is not
        # a real number. Group by pfr_id first, then prefer the "*TM" summary
        # row's totals when one exists; only sum individual stints ourselves
        # when PFR hasn't already done it (i.e. no such row is present).
        #
        # pfr_id is occasionally null, and pandas represents every null as the
        # same NaN — grouping on the raw value silently merged two different
        # real players who both lacked one (two different men both named
        # "Jaylon Jones", different teams) into a single inflated "player".
        # Fall back to name+team, which two same-named players on different
        # teams can't collide on, instead of grouping on a shared null.
        def _pfr_key(row) -> str:
            return str(row.pfr_id) if pd.notna(row.pfr_id) else f"noid:{row.player}:{row.tm}"

        rows_by_pfr: dict[str, list] = {}
        for row in defense.itertuples():
            pos = (row.pos or "").upper()
            if pos in NON_DEFENSIVE_POSITIONS:
                continue
            rows_by_pfr.setdefault(_pfr_key(row), []).append(row)

        def_totals: dict[str, dict] = {}
        for pfr_key, rows in rows_by_pfr.items():
            player_id = pfr_to_gsis.get(pfr_key, f"pfr:{pfr_key}")
            summary = next((r for r in rows if str(r.tm).endswith("TM")), None)
            stints = [r for r in rows if r is not summary]

            if summary is not None:
                sacks = float(summary.sk) if pd.notna(summary.sk) else 0.0
                tackles = float(summary.comb) if pd.notna(summary.comb) else 0.0
                ints = float(summary.int) if pd.notna(summary.int) else 0.0
                prss = float(summary.prss) if pd.notna(summary.prss) else 0.0
            else:
                sacks = sum(float(r.sk) for r in stints if pd.notna(r.sk))
                tackles = sum(float(r.comb) for r in stints if pd.notna(r.comb))
                ints = sum(float(r.int) for r in stints if pd.notna(r.int))
                prss = sum(float(r.prss) for r in stints if pd.notna(r.prss))

            last = stints[-1] if stints else rows[-1]
            def_totals[player_id] = {
                "name": last.player,
                "position": (last.pos or "").upper(),
                "team": last.tm,  # the real team code, never "2TM"
                "sacks": sacks,
                "tackles": tackles,
                "ints": ints,
                "prss": prss,
            }

        for player_id, agg in def_totals.items():
            record = pending.get((player_id, season)) or db.get(
                models.PlayerSeasonStats, {"player_id": player_id, "season": season}
            )
            if record is None:
                record = models.PlayerSeasonStats(
                    player_id=player_id, season=season, name=agg["name"], position=agg["position"], team=agg["team"]
                )
                db.add(record)
                pending[(player_id, season)] = record
                written += 1

            record.sacks = agg["sacks"]
            record.combined_tackles = agg["tackles"]
            record.def_interceptions = agg["ints"]
            record.pressures = agg["prss"]

        db.commit()
        logger.info("Loaded stats for %d players in season %d.", written, season)
        return written
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=None, help="e.g. 2024. Defaults to the most recently published season.")
    args = parser.parse_args()

    season = args.season
    if season is None:
        import datetime as dt

        season = _latest_available_season(dt.date.today().year)
        if season is None:
            raise SystemExit("Could not find any published player_stats season in the last 5 years.")
        logger.info("No --season given — using most recently published: %d", season)

    load_season(season)
