import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import sqlalchemy.exc
import bot.crud
from datetime import datetime
from db.schema import EventLog


# --- Tests for event schema constraints ---
# This user will be used for all tests
@pytest.fixture
def default_user(test_session):
    return bot.crud.get_or_create_user(test_session, "required_check", "RequiredTester")

def _expect_event_creation_failure(test_session, **override_fields):
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        bot.crud.create_event(
            session=test_session,
            event_id=override_fields.get("event_id", "missing_field_evt"),
            name=override_fields.get("name", "Missing Field Test"),
            type=override_fields.get("type", "test"),
            description=override_fields.get("description", "Testing required fields"),
            start_date=override_fields.get("start_date", "2025-01-01"),
            created_by=override_fields.get("created_by", "required_check")
        )
        test_session.commit()


def test_event_requires_event_id(test_session, default_user):
    _expect_event_creation_failure(test_session, event_id=None)


def test_event_requires_name(test_session, default_user):
    _expect_event_creation_failure(test_session, name=None)


def test_event_requires_type(test_session, default_user):
    _expect_event_creation_failure(test_session, type=None)


def test_event_requires_description(test_session, default_user):
    _expect_event_creation_failure(test_session, description=None)


def test_event_requires_start_date(test_session, default_user):
    _expect_event_creation_failure(test_session, start_date=None)


def test_event_requires_created_by(test_session, default_user):
    _expect_event_creation_failure(test_session, created_by=None)


def test_event_accepts_null_optional_fields(test_session):
    """end_date should be nullable (for ongoing events)."""
    bot.crud.get_or_create_user(test_session, "null1", "Tester")
    event = bot.crud.create_event(
        session=test_session,
        event_id="evt_null_end",
        name="No End Date",
        type="test",
        description="Ongoing event",
        start_date="2025-01-01",
        end_date=None,
        priority=0,
        shop_section_id=None,
        tags=None,
        embed_channel_id=None,
        embed_message_id=None,
        role_id=None,
        created_by="null1"
    )
    assert event.end_date is None


def test_event_id_unique_constraint(test_session):
    """Ensure event_id must be unique at the DB level."""
    bot.crud.get_or_create_user(test_session, "u1", "UniqTester")

    bot.crud.create_event(
        session=test_session,
        event_id="dupe_event",
        name="Original",
        type="test",
        description="Testing unique constraint",
        start_date="2025-01-01",
        end_date="2025-01-02",
        created_by="u1"
    )

    with pytest.raises(sqlalchemy.exc.IntegrityError):
        bot.crud.create_event(
            session=test_session,
            event_id="dupe_event",  # Should conflict
            name="Duplicate",
            type="test",
            description="Should fail",
            start_date="2025-01-03",
            end_date="2025-01-04",
            created_by="u1"
        )
        test_session.commit()