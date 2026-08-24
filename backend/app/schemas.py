import datetime as dt

from pydantic import BaseModel, ConfigDict


class OddsSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bookmaker: str
    market: str
    side: str
    price: int
    point: float | None
    fetched_at: dt.datetime
    is_closing: bool
    implied_prob: float | None = None


class GameOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    league: str
    season: int | None
    week: int | None
    commence_time: dt.datetime
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None
    completed: bool


class GameWithOddsOut(GameOut):
    odds: list[OddsSnapshotOut] = []


class LinesOut(BaseModel):
    game: GameOut
    bookmakers: dict[str, list[OddsSnapshotOut]]


class PickCreate(BaseModel):
    game_id: str
    market: str  # h2h | spreads | totals
    selection: str  # team name, "over", or "under"
    point: float | None = None
    entry_price: int
    stake: float = 1.0
    notes: str | None = None


class PickOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    game_id: str
    market: str
    selection: str
    point: float | None
    stake: float
    entry_price: int
    entry_time: dt.datetime
    closing_price: int | None
    closing_point: float | None
    clv: float | None
    result: str
    notes: str | None
    game: GameOut | None = None
