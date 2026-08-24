"""Bring an existing thepulse database up to the current models.

The MVP has never used Alembic — `init_db()` just runs `create_all`, which
creates missing *tables* but never alters an existing one. Adding player props
and futures changed the `picks` table (new `bet_type` / `player` columns, and
`game_id` had to become nullable so a futures pick can exist without a game);
bet slips added a `slip_id` column. An already-populated database needs this
one-off pass to pick up changes like those.

    python -m app.scripts.migrate

Safe to run repeatedly: every step checks the live schema first.
"""

import logging

from sqlalchemy import inspect, text

from app.database import engine, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# column name -> DDL fragment used when the column is missing from `picks`
NEW_PICK_COLUMNS = {
    "bet_type": "VARCHAR DEFAULT 'game'",
    "player": "VARCHAR",
    "slip_id": "INTEGER",
}

# Column order of the rebuilt `picks` table, used to copy rows across.
PICK_COLUMNS = [
    "id",
    "game_id",
    "bet_type",
    "market",
    "selection",
    "player",
    "point",
    "stake",
    "entry_price",
    "entry_time",
    "closing_price",
    "closing_point",
    "clv",
    "result",
    "notes",
    "slip_id",
]


def _add_missing_pick_columns(conn, existing: set[str]) -> None:
    for column, ddl in NEW_PICK_COLUMNS.items():
        if column in existing:
            continue
        conn.execute(text(f"ALTER TABLE picks ADD COLUMN {column} {ddl}"))
        logger.info("picks: added column %s", column)
    if "bet_type" not in existing:
        conn.execute(text("UPDATE picks SET bet_type = 'game' WHERE bet_type IS NULL"))


def _game_id_is_not_null(inspector) -> bool:
    for column in inspector.get_columns("picks"):
        if column["name"] == "game_id":
            return not column["nullable"]
    return False


def _rebuild_picks_sqlite(conn) -> None:
    """SQLite can't drop a NOT NULL constraint in place, so rebuild the table."""
    from app import models

    # A previous interrupted run can leave the scratch table behind.
    conn.execute(text("DROP TABLE IF EXISTS picks_old"))

    # RENAME TO carries the table's indexes along with it under their original
    # names, so `ix_picks_game_id` would still exist and collide the moment the
    # replacement table tries to create its own. Drop them first.
    for row in conn.execute(text("PRAGMA index_list('picks')")):
        name = row[1]
        if not name.startswith("sqlite_autoindex"):
            conn.execute(text(f'DROP INDEX IF EXISTS "{name}"'))

    conn.execute(text("ALTER TABLE picks RENAME TO picks_old"))
    models.Pick.__table__.create(bind=conn)
    columns = ", ".join(PICK_COLUMNS)
    conn.execute(text(f"INSERT INTO picks ({columns}) SELECT {columns} FROM picks_old"))
    conn.execute(text("DROP TABLE picks_old"))
    logger.info("picks: rebuilt with a nullable game_id")


def migrate() -> None:
    # Creates any brand-new tables (player_prop_snapshots, props_fetches,
    # futures_snapshots, api_usage). Existing tables are left alone.
    init_db()

    inspector = inspect(engine)
    if "picks" not in inspector.get_table_names():
        logger.info("No picks table yet — nothing to migrate.")
        return

    existing = {c["name"] for c in inspector.get_columns("picks")}
    dialect = engine.dialect.name

    with engine.begin() as conn:
        if dialect == "sqlite":
            conn.execute(text("PRAGMA foreign_keys=OFF"))
        _add_missing_pick_columns(conn, existing)

    inspector = inspect(engine)
    if _game_id_is_not_null(inspector):
        with engine.begin() as conn:
            if dialect == "sqlite":
                conn.execute(text("PRAGMA foreign_keys=OFF"))
                _rebuild_picks_sqlite(conn)
            else:
                conn.execute(text("ALTER TABLE picks ALTER COLUMN game_id DROP NOT NULL"))
                logger.info("picks: game_id is now nullable")
    else:
        logger.info("picks: game_id already nullable")

    logger.info("Migration complete.")


if __name__ == "__main__":
    migrate()
