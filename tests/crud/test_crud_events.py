import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import datetime
from db.schema import User, Event, EventLog
import bot.crud


@pytest.mark.crud
@pytest.mark.basic
def test_create_event(test_session,seed_user_and_event):
    event = seed_user_and_event(test_session)
    assert event.event_id == "test_event"
    assert event.name == "Test Event"
    assert event.type == "test"
    assert event.description == "A test event."
    assert event.start_date == "2025-01-01"
    assert event.created_by == "1234"


@pytest.mark.crud
@pytest.mark.basic
def test_get_event(test_session,seed_user_and_event):
    seed_user_and_event(test_session)
    event = bot.crud.get_event(test_session, "test_event")
    assert event is not None
    assert event.name == "Test Event"


@pytest.mark.crud
@pytest.mark.basic
def test_update_event(test_session,seed_user_and_event):
    seed_user_and_event(test_session)
    modified_at = str(datetime.utcnow())

    updated = bot.crud.update_event(
        session=test_session,
        event_id="test_event",
        modified_by="5678",
        modified_at=modified_at,
        reason="Fixing name",
        name="Updated Event"
    )

    assert updated is not None
    assert updated.name == "Updated Event"
    assert updated.modified_by == "5678"
    assert updated.modified_at == modified_at


@pytest.mark.crud
@pytest.mark.basic
def test_delete_event(test_session,seed_user_and_event):
    seed_user_and_event(test_session)
    deleted = bot.crud.delete_event(
        session=test_session,
        event_id="test_event",
        deleted_by="5678",
        reason="Testing deletion"
    )

    assert deleted is True
    assert bot.crud.get_event(test_session, "test_event") is None


@pytest.mark.crud
@pytest.mark.basic
def test_get_all_events(test_session,seed_user_and_event):
    seed_user_and_event(test_session, event_id="event1")
    seed_user_and_event(test_session, event_id="event2")
    events = bot.crud.get_all_events(test_session)
    assert len(events) >= 2
    assert all(isinstance(e, Event) for e in events)


@pytest.mark.crud
@pytest.mark.basic
def test_get_all_event_logs(test_session,seed_user_and_event):
    seed_user_and_event(test_session)
    bot.crud.update_event(
        session=test_session,
        event_id="test_event",
        modified_by="5678",
        modified_at=str(datetime.utcnow()),
        reason="Trigger log",
        name="New name"
    )
    bot.crud.delete_event(
        session=test_session,
        event_id="test_event",
        deleted_by="5678",
        reason="Testing deletion"
    )
    logs = bot.crud.get_all_event_logs(test_session)
    assert len(logs) >= 2  # 1 create + 1 edit
    assert any(log.EventLog.action == "create" for log in logs)
    assert any(log.EventLog.action == "edit" for log in logs)
    assert any(log.EventLog.action == "delete" for log in logs)