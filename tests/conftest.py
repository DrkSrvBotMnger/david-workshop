import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))			 
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.schema import Base
import bot.crud  # 👈 Required since crud is inside /bot

import datetime

# Create in-memory SQLite DB for testing										
@pytest.fixture(scope="function")
def test_session():
    engine = create_engine(os.environ["DATABASE_URL_TEST"])
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.rollback()
    session.close()
    Base.metadata.drop_all(engine)
    
# Shared test utility: user + event seeding
@pytest.fixture
def seed_user_and_event():
    def _seed(session, event_id="test_event"):
        bot.crud.get_or_create_user(session, "1234", "TestUser")
        return bot.crud.create_event(
            session=session,
            event_id=event_id,
            name="Test Event",
            type="test",
            description="A test event.",
            start_date="2025-01-01",
            created_by="1234"
        )
    return _seed
