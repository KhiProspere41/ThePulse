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


class PlayerPropOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bookmaker: str
    market: str
    player: str
    side: str  # over | under | yes | no
    price: int
    point: float | None
    fetched_at: dt.datetime
    implied_prob: float | None = None


class PlayerPropsOut(BaseModel):
    game: GameOut
    props: list[PlayerPropOut] = []
    markets: list[str] = []
    # "cached" | "fetched" | "quota_guard" | "error" | "not_found" | "unsupported_league"
    status: str
    fetched_at: dt.datetime | None = None
    stale: bool = False
    detail: str | None = None


class FuturesPriceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team: str
    bookmaker: str
    price: int
    fetched_at: dt.datetime
    implied_prob: float | None = None


class FuturesOut(BaseModel):
    sport_key: str
    market: str = "outrights"
    prices: list[FuturesPriceOut] = []
    status: str
    fetched_at: dt.datetime | None = None
    detail: str | None = None


class ApiUsageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    requests_used: int | None = None
    requests_remaining: int | None = None
    last_cost: int | None = None
    last_endpoint: str | None = None
    updated_at: dt.datetime | None = None


class PickCreate(BaseModel):
    # Optional so a futures pick ("win the Super Bowl") can be logged against a
    # season rather than a game.
    game_id: str | None = None
    bet_type: str = "game"  # game | player_prop | futures
    market: str  # h2h | spreads | totals | player_* | outrights
    selection: str  # team name, "over"/"under", or "yes"/"no"
    player: str | None = None  # required for bet_type="player_prop"
    point: float | None = None
    entry_price: int
    stake: float = 1.0
    notes: str | None = None


class PickOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    game_id: str | None
    bet_type: str
    market: str
    selection: str
    player: str | None
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
