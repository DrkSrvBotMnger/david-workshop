import pytest
from datetime import datetime, timezone
from db.schema import Reward, RewardEvent, EventLog, Event, EventStatus, RewardLog
from bot.crud.general_crud import log_change, is_linked_to_active_event
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


@pytest.mark.crud
@pytest.mark.basic
def test_is_linked_to_active_event_true(test_session, active_event, base_reward):
    """ Ensure is_linked_to_active_event returns True for linked active events. """
    test_session.flush()
    link = RewardEvent(
        reward_event_key="link_key",
        event_id=active_event.id,
        reward_id=base_reward.id,
        availability="inshop",
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(link)
    test_session.flush()

    assert is_linked_to_active_event(
        session=test_session,
        link_model=RewardEvent,
        link_field_name="reward_id",
        key_lookup_func=get_reward_by_key,
        public_key=base_reward.reward_key
    )

    test_session.commit()


@pytest.mark.crud
@pytest.mark.basic
def test_is_linked_to_active_event_false(test_session, base_reward):
    """ Ensure is_linked_to_active_event returns False for no linked active events. """
    def get_reward_by_key(sess, key):
        return sess.query(Reward).filter_by(reward_key=key).first()

    assert not is_linked_to_active_event(
        session=test_session,
        link_model=RewardEvent,
        link_field_name="reward_id",
        key_lookup_func=get_reward_by_key,
        public_key=base_reward.reward_key
    )

    test_session.commit()