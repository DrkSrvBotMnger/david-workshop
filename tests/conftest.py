import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))			

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.schema import Base
import bot.crud.users_crud
import bot.crud.events_crud

# Automatically set up and tear down the schema once per session
@pytest.fixture(scope="session", autouse=True)
def initialize_test_db():
    """
    Automatically sets up and tears down the test database schema
    once per test session. Applies to all tests.
    """
    test_db_url = os.environ["DATABASE_URL_TEST"]
    engine = create_engine(test_db_url)

    # Drop and recreate all tables for a clean start
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    yield  # Run tests

    # Drop tables after all tests complete
    Base.metadata.drop_all(engine)

# Provide a clean DB session per test				
@pytest.fixture(scope="function")
def test_session():

    engine = create_engine(os.environ["DATABASE_URL_TEST"])
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.rollback()
    session.close()



# Shared test utility: user + event seeding
@pytest.fixture
def seed_user_and_event():
    def _seed(session, event_id="test_event"):
        bot.crud.users_crud.get_or_create_user(session, "1234", "TestUser")
        return bot.crud.events_crud.create_event(
            session=session,
            event_id=event_id,
            name="Test Event",
            type="test",
            description="A test event.",
            start_date="2025-01-01",
            created_by="1234"
        )
    return _seed