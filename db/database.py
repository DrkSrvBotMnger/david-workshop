from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import os

# Use DATABASE_URL_DEV (dev) or DATABASE_URL (prod)
DATABASE_URL = os.getenv("DATABASE_URL_DEV") or os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Fallback to SQLite (local dev or automated tests)
    print("No DATABASE_URL found. Using SQLite fallback.")
    DATABASE_URL = "sqlite:///bot_database.db"

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Create session factory
SessionLocal = sessionmaker(bind=engine)

@contextmanager
def db_session():
    session = SessionLocal()
    try:
        yield session
        print("✅ Committing session...")
        session.commit()
    except Exception as e:
        print(f"❌ DB error: {e}")
        session.rollback()
        raise e
    finally:
        session.close()