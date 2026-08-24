from datetime import datetime

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    odds_api_key: str = ""
    odds_api_base_url: str = "https://api.the-odds-api.com/v4"
    database_url: str = "sqlite:///./thepulse.db"
    nfl_season_start: datetime = datetime(2026, 9, 10)
    cfb_season_start: datetime = datetime(2026, 9, 3)
    odds_refresh_interval_hours: int = 2
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
