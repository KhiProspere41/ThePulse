from datetime import datetime

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    odds_api_key: str = ""
    cfbd_api_key: str = ""
    odds_api_base_url: str = "https://api.the-odds-api.com/v4"
    database_url: str = "sqlite:///./thepulse.db"
    nfl_season_start: datetime = datetime(2026, 9, 10)
    cfb_season_start: datetime = datetime(2026, 9, 3)
    odds_refresh_interval_hours: int = 2
    frontend_origin: str = "http://localhost:5173"

    # --- Futures (outrights) ---------------------------------------------
    # The only NFL futures feed The Odds API publishes. Division winners and
    # season win totals are not available from any feed; app.simulate models
    # them instead.
    nfl_futures_sport_key: str = "americanfootball_nfl_super_bowl_winner"
    # Futures move slowly, and every refresh costs a credit, so this is daily
    # rather than tied to odds_refresh_interval_hours.
    futures_refresh_interval_hours: int = 24

    # --- Player props -----------------------------------------------------
    # Billed one credit per market per region per event, so keep this list
    # short and the cache long. These six have the widest book coverage.
    player_prop_markets: str = (
        "player_pass_yds,player_pass_tds,player_rush_yds,"
        "player_reception_yds,player_receptions,player_anytime_td"
    )
    # How long a game's cached props stay fresh before an on-demand view will
    # spend credits refetching them.
    player_props_cache_hours: int = 12
    # Refuse discretionary fetches (props, futures) once the monthly balance
    # drops below this, so the app keeps working on cached data instead of
    # going dark mid-month. Game lines are exempt: they are the core feature.
    odds_api_min_remaining: int = 25

    # --- Player season stats ------------------------------------------------
    # nflverse publishes each season's player_stats file only once it's over
    # (previous seasons; a season in progress has no file yet) — this checks
    # daily and loads it the first time it appears, so "current" stats/awards
    # advance on their own instead of needing a manual re-run each fall.
    player_stats_check_interval_hours: int = 24

    # --- Season simulation ------------------------------------------------
    sim_iterations: int = 10_000
    sim_cache_minutes: int = 30
    # Absolute ceiling on iterations for any simulation run, including ones
    # triggered internally (scripts, tests). 100k iterations measured ~23s of
    # wall time; this is a backstop against that, not just against a public
    # `iterations=` override — the API no longer exposes one at all.
    sim_max_iterations: int = 20_000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
