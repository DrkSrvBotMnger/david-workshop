import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))	

import pytest
import sqlalchemy.exc
from datetime import datetime, timezone
from db.schema import Reward, RewardLog, Event, EventStatus, RewardEvent
from bot.crud import rewards_crud


# --- CREATE ---
@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.reward
def test_create_reward_full_dict(test_session):
    """Create reward with full dict data and verify log."""
    data = {
        "reward_key": "crud_reward_full",
        "reward_type": "badge",
        "reward_name": "Full Dict Reward",
        "created_by": "tester"
    }
    reward = rewards_crud.create_reward(test_session, data)
    test_session.commit()

    # DB object
    assert reward.id is not None
    assert reward.reward_key == "crud_reward_full"

    # Log created
    logs = test_session.query(RewardLog).filter_by(reward_id=reward.id).all()
    assert any(log.log_action == "create" for log in logs)

    # Timestamp consistency
    log = logs[0]
    assert reward.created_at == log.performed_at


@pytest.mark.crud
@pytest.mark.reward
def test_create_reward_minimal_fields_defaults(test_session):
    """Create reward with minimal fields and check defaults."""
    data = {
        "reward_key": "crud_reward_min",
        "reward_type": "badge",
        "reward_name": "Minimal Reward",
        "created_by": "tester"
    }
    reward = rewards_crud.create_reward(test_session, data)
    test_session.commit()

    assert reward.is_released_on_active is False
    assert reward.is_stackable is False
    assert reward.number_granted == 0


@pytest.mark.crud
@pytest.mark.reward
def test_create_reward_missing_required_key(test_session):
    """Creating a reward without reward_key should fail."""
    data = {
        "reward_type": "badge",
        "reward_name": "No Key",
        "created_by": "tester"
    }
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        rewards_crud.create_reward(test_session, data)
        test_session.commit()


# --- READ ---
@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.reward
def test_get_reward_by_key(test_session, base_reward):
    """Fetch reward by key."""
    reward = rewards_crud.get_reward_by_key(test_session, base_reward.reward_key)
    assert reward is not None
    assert reward.reward_key == base_reward.reward_key


@pytest.mark.crud
@pytest.mark.reward
def test_get_all_rewards_and_filters(test_session, base_reward):
    """Ensure get_all_rewards returns expected objects and filters work."""
    results = rewards_crud.get_all_rewards(test_session)
    assert base_reward in results

    filtered = rewards_crud.get_all_rewards(test_session, reward_type=base_reward.reward_type)
    assert all(r.reward_type == base_reward.reward_type for r in filtered)


@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.reward
def test_reward_is_linked_to_active_event_true(test_session, base_reward, active_event):
    """Link reward to active event and verify detection."""
    link = RewardEvent(
        reward_event_key="link_key",
        event_id=active_event.id,
        reward_id=base_reward.id,
        availability="inshop",
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(link)
    test_session.commit()

    assert rewards_crud.reward_is_linked_to_active_event(
        test_session,
        base_reward.reward_key
    ) is True


@pytest.mark.crud
@pytest.mark.reward
def test_reward_is_linked_to_active_event_false(test_session, base_reward):
    """No active event linked."""
    assert rewards_crud.reward_is_linked_to_active_event(test_session, base_reward.reward_key) is False


# --- UPDATE ---
@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.reward
def test_update_reward_with_dict(test_session, base_reward):
    """Update reward name and verify."""
    update_data = {
        "reward_name": "Updated Name",
        "modified_by": "tester"
    }
    rewards_crud.update_reward(test_session, base_reward.reward_key, update_data, reason="Testing update")
    test_session.commit()

    updated = rewards_crud.get_reward_by_key(test_session, base_reward.reward_key)
    assert updated.reward_name == "Updated Name"

    # Log check
    logs = rewards_crud.get_reward_logs(test_session, log_action="edit")
    assert any("Reason: Testing update" in log.log_description for log in logs)

    # Timestamp consistency
    log = logs[0]
    assert updated.modified_at == log.performed_at


@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.reward
def test_update_reward_invalid_key(test_session):
    """Updating non-existing reward should return None."""
    result = rewards_crud.update_reward(test_session, "no_such_key", {"reward_name": "Nope"})
    assert result is None


@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.reward
def test_publish_preset_updates_fields(test_session, base_reward):
    """Publish preset and check updated fields + forced log."""
    rewards_crud.publish_preset(
        session=test_session,
        reward_key=base_reward.reward_key,
        use_channel_discord_id="123",
        use_message_discord_id="456",
        use_header_message_discord_id="789",
        set_by_discord_id="tester",
        forced=True
    )
    test_session.commit()

    reward = rewards_crud.get_reward_by_key(test_session, base_reward.reward_key)
    assert reward.use_channel_discord_id == "123"
    assert reward.preset_by == "tester"

    # Forced log check
    logs = rewards_crud.get_reward_logs(test_session)
    assert any("FORCED CHANGE" in log.log_description for log in logs)

    # Timestamp consistency
    log = logs[0]
    assert reward.modified_at == log.performed_at


@pytest.mark.crud
@pytest.mark.reward
def test_publish_preset_non_existing(test_session):
    """Publishing preset for missing reward returns None."""
    result = rewards_crud.publish_preset(
        session=test_session,
        reward_key="no_such_key",
        use_channel_discord_id="123",
        use_message_discord_id="456",
        use_header_message_discord_id="789",
        set_by_discord_id="tester"
    )
    assert result is None


# --- DELETE ---
@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.reward
def test_delete_reward_existing(test_session, base_reward):
    """Delete existing reward and check logs."""
    result = rewards_crud.delete_reward(
        test_session, base_reward.reward_key, performed_by="tester", reason="Testing delete"
    )
    test_session.commit()

    assert result is True
    assert test_session.query(Reward).filter_by(id=base_reward.id).count() == 0

    logs = rewards_crud.get_reward_logs(test_session, log_action="delete")
    assert any("Testing delete" in log.log_description for log in logs)


@pytest.mark.crud
@pytest.mark.reward
def test_delete_reward_non_existing(test_session):
    """Deleting missing reward returns False."""
    result = rewards_crud.delete_reward(test_session, "no_such_key", performed_by="tester", reason="No-op")
    assert result is False


# --- LOGS ---
@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.reward
def test_get_reward_logs_filters(test_session, base_reward):
    """Ensure log filters work."""
    rewards_crud.update_reward(test_session, base_reward.reward_key, {"reward_name": "Changed", "modified_by":"tester"})
    test_session.commit()

    all_logs = rewards_crud.get_reward_logs(test_session)
    assert len(all_logs) > 0

    filtered = rewards_crud.get_reward_logs(test_session, log_action="edit")
    assert all(log.log_action == "edit" for log in filtered)