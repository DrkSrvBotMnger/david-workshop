import pytest
import sqlalchemy.exc
from datetime import datetime, timezone
from db.schema import Event, EventLog, EventStatus
from bot.crud import events_crud


# --- CREATE ---
@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.event
def test_create_event_full_dict(test_session):
    """Create event with full dict data and verify log."""
    data = {
        "event_key": "crud_event_full",
        "event_name": "Full Dict Event",
        "event_type": "test",
        "event_description": "A fully specified event",
        "start_date": "2025-08-01",
        "created_by": "tester"
    }
    event = events_crud.create_event(test_session, data)
    test_session.commit()

    # DB object
    assert event.id is not None
    assert event.event_key == "crud_event_full"

    # Log created
    logs = test_session.query(EventLog).filter_by(event_id=event.id).all()
    assert any(log.log_action == "create" for log in logs)

    # Timestamp consistency
    log = logs[0]
    assert event.created_at == log.performed_at


@pytest.mark.crud
@pytest.mark.event
def test_create_event_minimal_fields_defaults(test_session):
    """Create event with minimal fields and check defaults."""
    data = {
        "event_key": "crud_event_min",
        "event_name": "Minimal Event",
        "event_type": "test",
        "event_description": "A minimal event",
        "start_date": "2025-08-01",
        "created_by": "tester"
    }
    event = events_crud.create_event(test_session, data)
    test_session.commit()

    assert event.priority == 0
    assert event.event_status == EventStatus.draft


@pytest.mark.crud
@pytest.mark.event
def test_create_event_missing_required_key(test_session):
    """Creating an event without event_key should fail."""
    data = {
        "event_name": "No Key Event",
        "event_type": "test",
        "event_description": "Missing key",
        "start_date": "2025-08-01",
        "created_by": "tester"
    }
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        events_crud.create_event(test_session, data)
        test_session.commit()


# --- READ ---
@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.event
def test_get_event_by_key(test_session, base_event):
    """Fetch event by key."""
    event = events_crud.get_event_by_key(test_session, base_event.event_key)
    assert event is not None
    assert event.event_key == base_event.event_key


@pytest.mark.crud
@pytest.mark.event
def test_get_all_events_and_filters(test_session, base_event):
    """Ensure get_all_events returns expected objects and filters work."""
    results = events_crud.get_all_events(test_session)
    assert base_event in results

    filtered = events_crud.get_all_events(test_session, event_status=base_event.event_status.value)
    assert all(e.event_status == base_event.event_status for e in filtered)


@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.event
def test_is_event_active_true(test_session):
    """Event should be active when status is active."""
    data = {
        "event_key": "crud_event_active",
        "event_name": "Active Event",
        "event_type": "test",
        "event_description": "An active event",
        "start_date": "2025-08-01",
        "created_by": "tester",
        "event_status": EventStatus.active
    }
    event = events_crud.create_event(test_session, data)
    test_session.commit()

    assert events_crud.is_event_active(test_session, event.event_key) is True


@pytest.mark.crud
@pytest.mark.event
def test_is_event_active_false(test_session, base_event):
    """Event should not be active unless status is active."""
    assert events_crud.is_event_active(test_session, base_event.event_key) is False


# --- UPDATE ---
@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.event
def test_update_event_with_dict(test_session, base_event):
    """Update event name and verify."""
    update_data = {
        "event_name": "Updated Event Name",
        "modified_by": "tester"
    }
    events_crud.update_event(test_session, base_event.event_key, update_data, reason="Testing update")
    test_session.commit()

    updated = events_crud.get_event_by_key(test_session, base_event.event_key)
    assert updated.event_name == "Updated Event Name"

    # Log check
    logs = events_crud.get_event_logs(test_session, log_action="edit")
    assert any("Reason: Testing update" in log.log_description for log in logs)

    # Timestamp consistency
    log = logs[0]
    assert updated.modified_at == log.performed_at


@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.event
def test_update_event_invalid_key(test_session):
    """Updating non-existing event should return None."""
    result = events_crud.update_event(test_session, "no_such_event", {"event_name": "Nope"})
    assert result is None


@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.event
def test_set_event_status_updates_status(test_session, base_event):
    """Set event status and verify."""
    events_crud.set_event_status(
        session=test_session,
        event_key=base_event.event_key,
        status_update_data={
            "event_status": EventStatus.active,
            "modified_by": "tester"
        }
    )
    test_session.commit()

    updated = events_crud.get_event_by_key(test_session, base_event.event_key)
    assert updated.event_status == EventStatus.active

    # Log check
    logs = events_crud.get_event_logs(test_session)
    assert any("status changed to active" in log.log_description for log in logs)

    # Timestamp consistency
    log = logs[0]
    assert updated.modified_at == log.performed_at
    

# --- DELETE ---
@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.event
def test_delete_event_existing(test_session, base_event):
    """Delete existing event and check logs."""
    result = events_crud.delete_event(
        test_session, base_event.event_key, performed_by="tester", reason="Testing delete"
    )
    test_session.commit()

    assert result is True
    assert test_session.query(Event).filter_by(id=base_event.id).count() == 0

    logs = events_crud.get_event_logs(test_session, log_action="delete")
    assert any("Testing delete" in log.log_description for log in logs)


@pytest.mark.crud
@pytest.mark.event
def test_delete_event_non_existing(test_session):
    """Deleting missing event returns False."""
    result = events_crud.delete_event(test_session, "no_such_event", performed_by="tester", reason="No-op")
    assert result is False


# --- LOGS ---
@pytest.mark.crud
@pytest.mark.event
def test_get_event_logs_filters(test_session, base_event):
    """Ensure log filters work."""
    events_crud.update_event(
        test_session,
        base_event.event_key,
        {"event_name": "Changed Name", "modified_by": "tester"}
    )
    test_session.commit()

    all_logs = events_crud.get_event_logs(test_session)
    assert len(all_logs) > 0

    filtered = events_crud.get_event_logs(test_session, log_action="edit")
    assert all(log.log_action == "edit" for log in filtered)
