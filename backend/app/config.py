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

    # --- Season simulation ------------------------------------------------
    sim_iterations: int = 10_000
    sim_cache_minutes: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
