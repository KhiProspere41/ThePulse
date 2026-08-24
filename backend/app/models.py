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
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), index=True)
    market: Mapped[str] = mapped_column(String)  # h2h | spreads | totals
    selection: Mapped[str] = mapped_column(String)  # team name, "over", or "under"
    point: Mapped[float | None] = mapped_column(Float, nullable=True)
    stake: Mapped[float] = mapped_column(Float, default=1.0)

    entry_price: Mapped[int] = mapped_column(Integer)
    entry_time: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    closing_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closing_point: Mapped[float | None] = mapped_column(Float, nullable=True)
    clv: Mapped[float | None] = mapped_column(Float, nullable=True)  # implied-prob edge, in %

    result: Mapped[str] = mapped_column(String, default="pending")  # pending|win|loss|push
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    game: Mapped["Game"] = relationship(back_populates="picks")


class TeamElo(Base):
    __tablename__ = "team_elo"

    team: Mapped[str] = mapped_column(String, primary_key=True)
    league: Mapped[str] = mapped_column(String, primary_key=True)
    rating: Mapped[float] = mapped_column(Float, default=1500.0)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
