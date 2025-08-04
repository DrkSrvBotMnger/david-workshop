import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))	

import pytest
from factories import *  # Import all fixtures from factories.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.schema import Base


# --- Load PostgreSQL test DB URL from environment secret ---
# Example: "postgresql+psycopg2://user:pass@localhost:5432/test_db"
TEST_DATABASE_URL = os.getenv("DATABASE_URL_TEST")
if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL environment variable not set! "
        "Make sure your test DB connection string is in your secrets."
    )

# --- Create engine once per test session ---
@pytest.fixture(scope="session")
def engine():
    """Create the PostgreSQL engine for tests."""
    engine = create_engine(TEST_DATABASE_URL)
    # Ensure schema exists
    Base.metadata.create_all(engine)
    return engine

# --- Create a new database session for each test function ---
@pytest.fixture(scope="function")
def test_session(engine):
    """
    Creates a new database session for a test inside a transaction.
    Rolls back after each test so changes do not persist.
    """
    connection = engine.connect()
    transaction = connection.begin()

    Session = sessionmaker(bind=connection)
    session = Session()

    yield session  # test runs here

    session.close()
    if transaction.is_active:  # <--- prevents warnings
        transaction.rollback()

    connection.close()