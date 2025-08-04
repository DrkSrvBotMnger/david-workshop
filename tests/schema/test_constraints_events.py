import pytest
from datetime import datetime, timezone
import sqlalchemy.exc
from sqlalchemy import text
from db.schema import Event, EventStatus


# --- Mandatory fields ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.parametrize("field", [
    "event_key",
    "event_name",
    "event_type",
    "event_description",
    "start_date",
    "created_by"
])
def test_e_mandatory_fields_missing(test_session, field):
    """Ensure mandatory fields cannot be NULL."""
    kwargs = {
        "event_key":"event_key1",
        "event_name":"Constraint Test",
        "event_type":"test",
        "event_description":"test",
        "start_date":"2025-01-01",
        "priority":0,
        "created_by":"9999",
        "created_at":datetime.now(timezone.utc).isoformat(),
        "event_status":"draft"
    }
    kwargs[field] = None
    e = Event(**kwargs)
    test_session.add(e)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.commit()


# --- Nullable fields ---
@pytest.mark.schema
@pytest.mark.event
def test_e_accepts_null_optional_fields(test_session):
    """end_date, coordinator_discord_id, tags, embed_channel_discord_id, embed_message_discord_id, role_discord_id, modified_by, modified_at should be nullable."""
    e = Event(
        event_key="null_optional_fields_evt",
        event_name="Constraint Test",
        event_type="test",
        event_description="test",
        start_date="2025-01-01",
        end_date=None,
        coordinator_discord_id=None,
        priority=0,
        tags=None,
        embed_channel_discord_id=None,
        embed_message_discord_id=None,
        role_discord_id=None,
        created_by="9999",
        created_at=datetime.now(timezone.utc).isoformat(),
        modified_by=None,
        modified_at=None,
        event_status=EventStatus.draft
    )
    test_session.add(e)
    test_session.commit()

    assert e.end_date is None
    assert e.coordinator_discord_id is None
    assert e.tags is None
    assert e.embed_channel_discord_id is None
    assert e.embed_message_discord_id is None
    assert e.role_discord_id is None
    assert e.modified_by is None
    assert e.modified_at is None


# --- Forced-NULL ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.asyncio 
async def test_priority_column_is_not_nullable(test_session):
    """priority should not be nullable."""
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.execute(text(""" INSERT INTO events (event_key, event_name, event_type, event_description, start_date, priority, created_by, created_at, event_status) VALUES ('eid', 'null_priority_evt', 'typ','should fail','2025-01-01', NULL, 'test user', '2025-08-03T03:00:00.000000', 'draft')"""))
        test_session.commit()


@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.asyncio 
async def test_event_status_column_is_not_nullable(test_session): 
    """event_status should not be nullable."""
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.execute(text(""" INSERT INTO events (event_key, event_name, event_type, event_description, start_date, priority, created_by, created_at, event_status) VALUES ('eid', 'null_event_status_evt', 'typ','should fail','2025-01-01', 0, 'test user', '2025-08-03T03:00:00.000000', NULL)"""))
        test_session.commit()


# --- Defaults ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.event
def test_event_default_values_are_correct(test_session):
    """Ensure Event defaults are correct for priority and event_status."""
    e = Event(
        event_key="default_event",
        event_name="Default Event",
        event_type="test",
        event_description="Test event defaults",
        start_date="2025-01-01",
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(e)
    test_session.commit()

    assert e.priority == 0
    assert e.event_status.name == "draft"


# --- Unique key ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.event
def test_event_key_unique_constraint(test_session, base_event):
    """Ensure event_key must be unique at the DB level."""
    event2 = Event(
        event_key=base_event.event_key,  # duplicate key
        event_name="Constraint Test",
        event_type="test",
        event_description="test",
        start_date="2025-01-01",
        priority=0,
        created_by="9999",
        created_at=datetime.now(timezone.utc).isoformat(),
        event_status=EventStatus.draft
    )
    test_session.add(event2)

    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.commit()