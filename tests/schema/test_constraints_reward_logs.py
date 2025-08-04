import pytest
import sqlalchemy.exc
from datetime import datetime, timezone
from db.schema import RewardLog


# --- Mandatory fields ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.reward
@pytest.mark.log
@pytest.mark.parametrize("field", [
    "log_action",
    "performed_by",
    "performed_at"
])
def test_rl_mandatory_fields_missing(test_session, field):
    """Ensure mandatory fields cannot be NULL."""
    kwargs = {
        "reward_id": None,
        "log_action": "create",
        "performed_by": "tester",
        "performed_at": datetime.now(timezone.utc).isoformat()
    }
    kwargs[field] = None
    rl = RewardLog(**kwargs)
    test_session.add(rl)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.commit()


# --- Nullable fields ---
@pytest.mark.schema
@pytest.mark.reward
@pytest.mark.log
def test_rel_accepts_null_optional_fields(test_session):
    """Ensure reward_id and log_description can be NULL."""    
    rl = RewardLog(
        reward_id=None,
        log_action="create",
        performed_by="mod123",
        performed_at="2025-01-01T00:00:00",
        log_description=None
    )
    test_session.add(rl)
    test_session.commit()

    assert rl.reward_id is None
    assert rl.log_description is None


# --- FK IS NULL (reward_id) ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.reward
@pytest.mark.log
def test_rl_reward_id_set_null_on_delete(test_session, base_reward):
    """Ensure deleting an Reward sets reward_id to NULL in RewardLog."""
    rl = RewardLog(
        reward_id=base_reward.id,
        log_action="edit",
        performed_by="9999",
        performed_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(rl)
    test_session.commit()

    # Delete reward
    test_session.delete(base_reward)
    test_session.commit()

    # Verify reward_id in logs is now NULL
    logs = test_session.query(RewardLog).all()
    assert all(rl.reward_id is None for rl in logs)