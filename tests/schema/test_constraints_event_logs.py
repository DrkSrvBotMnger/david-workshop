import pytest
import sqlalchemy.exc
from datetime import datetime, timezone
from db.schema import EventLog


# --- Mandatory fields ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.log
@pytest.mark.parametrize("field", [
    "log_action",
    "performed_by",
    "performed_at"
])
def test_el_mandatory_fields_missing(test_session, field):
    """Ensure mandatory fields cannot be NULL."""
    kwargs = {
        "event_id": None,
        "log_action": "create",
        "performed_by": "tester",
        "performed_at": datetime.now(timezone.utc).isoformat()
    }
    kwargs[field] = None
    el = EventLog(**kwargs)
    test_session.add(el)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.commit()


# --- Nullable fields ---
@pytest.mark.schema
@pytest.mark.event
@pytest.mark.log
def test_el_accepts_null_optional_fields(test_session):
    """Ensure log_description can be NULL."""
    el = EventLog(
        event_id=None,
        log_action="create",
        performed_by="mod123",
        performed_at="2025-01-01T00:00:00",
        log_description=None
    )
    test_session.add(el)
    test_session.commit()

    assert el.event_id is None
    assert el.log_description is None


# --- FK IS NULL (event_id) ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.log
def test_el_event_id_set_null_on_delete(test_session, base_event):
    """Ensure deleting an Event sets event_id to NULL in EventLog."""
    el = EventLog(
        event_id=base_event.id,
        log_action="edit",
        performed_by="9999",
        performed_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(el)
    test_session.commit()
    
    # Delete event
    test_session.delete(base_event)
    test_session.commit()

    # Verify event_id in logs is now NULL
    logs = test_session.query(EventLog).all()
    assert all(el.event_id is None for el in logs)