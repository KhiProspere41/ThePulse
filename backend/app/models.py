import datetime as dt

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Game(Base):
    __tablename__ = "games"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    league: Mapped[str] = mapped_column(String, index=True)  # "nfl" | "college"
    season: Mapped[int | None] = mapped_column(Integer, nullable=True)
    week: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    commence_time: Mapped[dt.datetime] = mapped_column(DateTime, index=True)
    home_team: Mapped[str] = mapped_column(String)
    away_team: Mapped[str] = mapped_column(String)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String, default="odds_api")

    odds_snapshots: Mapped[list["OddsSnapshot"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
    player_props: Mapped[list["PlayerPropSnapshot"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
    picks: Mapped[list["Pick"]] = relationship(back_populates="game")


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), index=True)
    bookmaker: Mapped[str] = mapped_column(String, index=True)
    market: Mapped[str] = mapped_column(String, index=True)  # h2h | spreads | totals
    side: Mapped[str] = mapped_column(String)  # home | away | over | under
    price: Mapped[int] = mapped_column(Integer)  # American odds
    point: Mapped[float | None] = mapped_column(Float, nullable=True)  # spread or total
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, index=True)
    is_closing: Mapped[bool] = mapped_column(Boolean, default=False)

    game: Mapped["Game"] = relationship(back_populates="odds_snapshots")


class Pick(Base):
    __tablename__ = "picks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Nullable because futures picks ("win the Super Bowl") belong to a season,
    # not to any single game.
    game_id: Mapped[str | None] = mapped_column(ForeignKey("games.id"), nullable=True, index=True)
    bet_type: Mapped[str] = mapped_column(String, default="game", index=True)  # game | player_prop | futures
    market: Mapped[str] = mapped_column(String)  # h2h | spreads | totals | player_* | outrights
    selection: Mapped[str] = mapped_column(String)  # team name, "over"/"under", or "yes"/"no"
    player: Mapped[str | None] = mapped_column(String, nullable=True)  # player props only
    point: Mapped[float | None] = mapped_column(Float, nullable=True)
    stake: Mapped[float] = mapped_column(Float, default=1.0)

    entry_price: Mapped[int] = mapped_column(Integer)
    entry_time: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    closing_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closing_point: Mapped[float | None] = mapped_column(Float, nullable=True)
    clv: Mapped[float | None] = mapped_column(Float, nullable=True)  # implied-prob edge, in %

    result: Mapped[str] = mapped_column(String, default="pending")  # pending|win|loss|push
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    game: Mapped["Game | None"] = relationship(back_populates="picks")


class TeamElo(Base):
    __tablename__ = "team_elo"

    team: Mapped[str] = mapped_column(String, primary_key=True)
    league: Mapped[str] = mapped_column(String, primary_key=True)
    rating: Mapped[float] = mapped_column(Float, default=1500.0)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class PlayerPropSnapshot(Base):
    """One player-prop outcome from one bookmaker at one point in time.

    Player props come from The Odds API's per-event endpoint, which is billed
    per market per region *per event* — so unlike game lines these are fetched
    on demand and cached (see `ingest.ingest_player_props`), never polled.
    """

    __tablename__ = "player_prop_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), index=True)
    bookmaker: Mapped[str] = mapped_column(String, index=True)
    market: Mapped[str] = mapped_column(String, index=True)  # player_pass_yds, player_anytime_td, ...
    player: Mapped[str] = mapped_column(String, index=True)
    side: Mapped[str] = mapped_column(String)  # over | under | yes | no
    price: Mapped[int] = mapped_column(Integer)  # American odds
    point: Mapped[float | None] = mapped_column(Float, nullable=True)  # the line, absent for anytime-TD
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, index=True)
    is_closing: Mapped[bool] = mapped_column(Boolean, default=False)

    game: Mapped["Game"] = relationship(back_populates="player_props")


class PropsFetch(Base):
    """Cache marker for player-prop fetches, one row per game.

    Tracked separately from the snapshots themselves so that a game whose books
    simply have no props posted yet is still recorded as "checked recently" and
    doesn't get re-requested (and re-billed) on every page view.
    """

    __tablename__ = "props_fetches"

    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), primary_key=True)
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    outcome_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String, nullable=True)


class FuturesSnapshot(Base):
    """An outright (futures) price for a team, e.g. to win the Super Bowl."""

    __tablename__ = "futures_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    league: Mapped[str] = mapped_column(String, index=True, default="nfl")
    sport_key: Mapped[str] = mapped_column(String, index=True)  # americanfootball_nfl_super_bowl_winner
    market: Mapped[str] = mapped_column(String, default="outrights")
    team: Mapped[str] = mapped_column(String, index=True)  # full team name as the book publishes it
    bookmaker: Mapped[str] = mapped_column(String, index=True)
    price: Mapped[int] = mapped_column(Integer)  # American odds
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, index=True)


class ApiUsage(Base):
    """Latest quota headers returned by The Odds API.

    The free tier is 500 requests/month and the per-event props endpoint bills
    one credit per market returned, so knowing the remaining balance is the
    difference between a demo that works all month and one that dies on day two.
    """

    __tablename__ = "api_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    requests_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requests_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_cost: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_endpoint: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class ScheduledGame(Base):
    """The full published season schedule, keyed by nflverse game id.

    Kept separate from `games` on purpose. `games` is the odds board — one row
    per event the sportsbooks have posted, which in-season is only the next
    week or two. The season simulator needs all 272 games, including ones no
    book has priced yet, and mixing those into `games` would put phantom
    rows with no odds on the games page and duplicate every live event under a
    second id. Loaded by `app.scripts.load_schedule`.

    Team columns hold nflverse abbreviations, matching `team_elo`.
    """

    __tablename__ = "scheduled_games"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    week: Mapped[int] = mapped_column(Integer, index=True)
    kickoff: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    home_team: Mapped[str] = mapped_column(String, index=True)
    away_team: Mapped[str] = mapped_column(String, index=True)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)


class PlayerSeasonStats(Base):
    """One player's cumulative regular-season stats for one NFL season.

    Sourced from nflverse's published `player_stats_{season}.parquet` (offense:
    passing/rushing/receiving) and its Pro-Football-Reference defensive mirror
    (sacks/tackles/INTs), joined on the seasonal roster for name/position/team.
    Loaded by `app.scripts.load_player_stats`. Both halves can be null for a
    given row — a pure defender has no passing_yards, a pure offensive player
    has no sacks.
    """

    __tablename__ = "player_season_stats"

    player_id: Mapped[str] = mapped_column(String, primary_key=True)
    season: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    position: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    team: Mapped[str | None] = mapped_column(String, nullable=True)
    games: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Offense
    completions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passing_yards: Mapped[float | None] = mapped_column(Float, nullable=True)
    passing_tds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interceptions: Mapped[int | None] = mapped_column(Integer, nullable=True)  # thrown
    carries: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rushing_yards: Mapped[float | None] = mapped_column(Float, nullable=True)
    rushing_tds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    receptions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    targets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    receiving_yards: Mapped[float | None] = mapped_column(Float, nullable=True)
    receiving_tds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fantasy_points: Mapped[float | None] = mapped_column(Float, nullable=True)
    fantasy_points_ppr: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Defense (Pro-Football-Reference advanced stats)
    sacks: Mapped[float | None] = mapped_column(Float, nullable=True)
    combined_tackles: Mapped[float | None] = mapped_column(Float, nullable=True)
    def_interceptions: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressures: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Offense advanced (Pro-Football-Reference) — supplements, not replaces,
    # the core offense columns above, which come from nflverse's own file.
    # PFR's advanced passing table carries pressure/accuracy context but not
    # the core yards/TD counting stats, so it's additive rather than a swap.
    passing_pressure_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    passing_on_tgt_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    passing_air_yards_per_att: Mapped[float | None] = mapped_column(Float, nullable=True)
    rush_yards_before_contact: Mapped[float | None] = mapped_column(Float, nullable=True)
    rush_yards_after_contact: Mapped[float | None] = mapped_column(Float, nullable=True)
    rush_broken_tackles: Mapped[float | None] = mapped_column(Float, nullable=True)
    rec_yards_after_catch: Mapped[float | None] = mapped_column(Float, nullable=True)
    rec_avg_depth_of_target: Mapped[float | None] = mapped_column(Float, nullable=True)
    rec_broken_tackles: Mapped[float | None] = mapped_column(Float, nullable=True)
    rec_drop_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
