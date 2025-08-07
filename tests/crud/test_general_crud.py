import pytest
from datetime import datetime, timezone
from db.schema import Reward, RewardEvent, EventLog, Event, EventStatus, RewardLog
from bot.crud.general_crud import log_change
from bot.crud.rewards_crud import get_reward_by_key


@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.log
def test_log_change_creates_log(test_session, base_reward):
    """Ensure log_change creates a log entry with the correct details."""
    log = log_change(
        session=test_session,
        log_model=RewardLog,
        fk_field="reward_id",
        fk_value=base_reward.id,  # will be flushed later
        log_action="create",
        performed_by="tester",
        performed_at=datetime.now(timezone.utc).isoformat(),
        log_description="Test log"
    )
    test_session.commit()
    assert log.reward_id == base_reward.id
    assert log.log_action == "create"
    assert log.log_description == "Test log"


@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.log
def test_log_change_forced_prefix(test_session, base_event):
    """Ensure forced logs have the correct prefix."""
    log = log_change(
        session=test_session,
        log_model=EventLog,
        fk_field="event_id",
        fk_value=base_event.id,
        log_action="edit",
        performed_by="tester",
        performed_at=datetime.now(timezone.utc).isoformat(),
        log_description="Manual override",
        forced=True
    )
    test_session.commit()
    assert "⚠️ **FORCED CHANGE**" in log.log_description
