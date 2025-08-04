import pytest
import sqlalchemy.exc
from datetime import datetime, timezone
from db.schema import RewardEventLog


# --- Mandatory fields ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.reward_event
@pytest.mark.log
@pytest.mark.parametrize("field", [
    "log_action",
    "performed_by",
    "performed_at"
])
def test_rel_mandatory_fields_missing(test_session, field):
    """Ensure mandatory fields cannot be NULL."""
    kwargs = {
        "reward_event_id": None,
        "log_action": "create",
        "performed_by": "tester",
        "performed_at": datetime.now(timezone.utc).isoformat()
    }
    kwargs[field] = None
    rel = RewardEventLog(**kwargs)
    test_session.add(rel)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.commit()


# --- Nullable fields ---
@pytest.mark.schema
@pytest.mark.reward_event
@pytest.mark.log
def test_rel_accepts_null_optional_fields(test_session):
    """Ensure reward_event_id and log_description can be NULL."""
    rel = RewardEventLog(
        reward_event_id=None,
        log_action="create",
        performed_by="mod123",
        performed_at="2025-01-01T00:00:00",
        log_description=None
    )
    test_session.add(rel)
    test_session.commit()

    assert rel.reward_event_id is None
    assert rel.log_description is None


# --- FK IS NULL (reward_event_id) ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.reward_event
@pytest.mark.log
def test_rel_reward_event_id_set_null_on_delete(test_session, base_reward_event):
    rel = RewardEventLog(
        reward_event_id=base_reward_event.id,
        log_action="edit",
        performed_by="9999",
        performed_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(rel)
    test_session.commit()
    
    # Delete reward_event
    test_session.delete(base_reward_event)
    test_session.commit()

    # Verify reward_event_id in logs is now NULL
    logs = test_session.query(RewardEventLog).all()
    assert all(rel.reward_event_id is None for rel in logs)