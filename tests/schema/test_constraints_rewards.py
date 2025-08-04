import pytest
from datetime import datetime, timezone
import sqlalchemy.exc
from sqlalchemy import text
from db.schema import Reward


# --- Mandatory fields ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.reward
@pytest.mark.parametrize("field", [
    "reward_key",
    "reward_type",
    "reward_name",
    "created_by",
    "created_at"
])
def test_r_mandatory_fields_missing(test_session, base_event, base_reward, field):
    """Ensure mandatory fields cannot be NULL."""
    kwargs = {
        "reward_key": "key1",
        "reward_type": base_event.id,
        "reward_name": base_reward.id,
        "is_released_on_active": False,
        "is_stackable": False,
        "number_granted": 0,
        "created_by": "tester",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    kwargs[field] = None
    r = Reward(**kwargs)
    test_session.add(r)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.commit()
        

# --- Nullable fields ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.reward
def test_r_accepts_null_optional_fields(test_session):
    """reward_description, emoji, use_channel_discord_id, use_message_discord_id, use_header_message_discord_id, use_template, use_allowed_params, use_media_mode, is_stackable, number_granted"""
    r = Reward(
        reward_key="requires_created_at_rew",
        reward_type="test",
        reward_name="Constraint Test",
        reward_description=None,
        is_released_on_active=False,
        emoji=None,
        use_channel_discord_id=None,
        use_message_discord_id=None,   
        use_header_message_discord_id=None,
        use_template=None,
        use_allowed_params=None,
        use_media_mode=None,
        is_stackable=False,
        number_granted=0,
        created_by="9999",
        created_at=datetime.now(timezone.utc).isoformat(),
        modified_by=None,
        modified_at=None,
        preset_by=None,
        preset_at=None
    )

    test_session.add(r)
    test_session.commit()

    assert r.reward_description is None
    assert r.emoji is None
    assert r.use_channel_discord_id is None
    assert r.use_message_discord_id is None
    assert r.use_header_message_discord_id is None
    assert r.use_template is None
    assert r.use_allowed_params is None
    assert r.use_media_mode is None
    assert r.modified_by is None
    assert r.modified_at is None
    assert r.preset_by is None
    assert r.preset_at is None


# --- Forced-NULL ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.reward
@pytest.mark.asyncio 
async def test_is_released_on_active_column_is_not_nullable(test_session): 
    """is_released_on_active should not be nullable."""
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.execute(text(""" INSERT INTO rewards (reward_key, reward_type, reward_name, is_released_on_active, is_stackable, number_granted, created_by, created_at) VALUES ('rid', 'test', 'null_is_released_on_active_rew', NULL, False, 0, '9999', '2025-08-03T03:00:00.000000')"""))
        test_session.commit()


@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.reward
@pytest.mark.asyncio 
async def test_is_stackable_column_is_not_nullable(test_session): 
    """is_stackable should not be nullable."""
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.execute(text(""" INSERT INTO rewards (reward_key, reward_type, reward_name, is_released_on_active, is_stackable, number_granted, created_by, created_at) VALUES ('rid', 'test', 'null_is_stackable_rew', False, NULL, 0, '9999', '2025-08-03T03:00:00.000000')"""))
        test_session.commit()


@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.reward
@pytest.mark.asyncio 
async def test_number_granted_on_active_column_is_not_nullable(test_session): 
    """number_granted should not be nullable."""
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.execute(text(""" INSERT INTO rewards (reward_key, reward_type, reward_name, is_released_on_active, is_stackable, number_granted, created_by, created_at) VALUES ('rid', 'test', 'null_number_granted_rew', False, False, NULL, '9999', '2025-08-03T03:00:00.000000')"""))
        test_session.commit()


# --- Defaults ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.reward
def test_reward_default_values_are_correct(test_session):
    """Ensure Reward defaults are correct for is_released_on_active, is_stackable, and number_granted."""
    r = Reward(
        reward_key="default_reward",
        reward_type="test",
        reward_name="Test Reward Defaults",
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(r)
    test_session.commit()

    assert r.is_released_on_active is False
    assert r.is_stackable is False
    assert r.number_granted == 0


# --- Unique key ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.reward
def test_reward_key_unique_constraint(test_session, base_reward):
    """Ensure reward_key must be unique at the DB level."""
    r2 = Reward(
        reward_key=base_reward.reward_key,
        reward_name="Constraint Test",
        reward_type="test",
        reward_description="test",
        created_by="9999",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(r2)

    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.commit()