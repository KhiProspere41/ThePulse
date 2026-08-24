"""Creates all tables from the SQLAlchemy models. Run with: python -m app.scripts.init_db
(The FastAPI app also calls this automatically on startup — this script is for
running the migration standalone, e.g. before load_historical_data.py.)"""

from app.database import init_db

if __name__ == "__main__":
    init_db()
    print("Database tables created.")
