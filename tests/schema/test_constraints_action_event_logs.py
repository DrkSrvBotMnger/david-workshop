import pytest
import sqlalchemy.exc
from datetime import datetime, timezone
from db.schema import ActionEventLog


# --- Mandatory fields ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action_event
@pytest.mark.log
@pytest.mark.parametrize("field", [
    "log_action",
    "performed_by",
    "performed_at"
])
def test_ael_mandatory_fields_missing(test_session, field):
    """Ensure mandatory fields cannot be NULL."""
    kwargs = {
        "action_event_id": None,
        "log_action": "create",
        "performed_by": "tester",
        "performed_at": datetime.now(timezone.utc).isoformat()
    }
    kwargs[field] = None
    ael = ActionEventLog(**kwargs)
    test_session.add(ael)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.commit()


# --- Nullable fields ---
@pytest.mark.schema
@pytest.mark.action_event
@pytest.mark.log
def test_ael_accepts_null_optional_fields(test_session):
    """Ensure log_description can be NULL."""
    ael = ActionEventLog(
        action_event_id=None,
        log_action="create",
        performed_by="mod123",
        performed_at="2025-01-01T00:00:00",
        log_description=None
    )
    test_session.add(ael)
    test_session.commit()

    assert ael.action_event_id is None
    assert ael.log_description is None


# --- FK IS NULL (action_event_id) ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action_event
@pytest.mark.log
def test_ael_action_event_id_set_null_on_delete(test_session, base_action_event):
    """Ensure deleting an ActionEvent sets action_event_id to NULL in ActionEventLog."""
    ael = ActionEventLog(
        action_event_id=base_action_event.id,
        log_action="edit",
        performed_by="9999",
        performed_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(ael)
    test_session.flush()
    
    # Delete action_event
    test_session.delete(base_action_event)
    test_session.commit()

    # Verify action_event in logs is now NULL
    logs = test_session.query(ActionEventLog).all()
    assert all(ael.action_event_id is None for ael in logs)