import pytest
import sqlalchemy.exc
from sqlalchemy import text
from datetime import datetime, timezone
from db.schema import RewardEvent


# --- Mandatory fields ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.reward_event
@pytest.mark.parametrize("field", [
    "reward_event_key",
    "event_id",
    "reward_id",
    "created_by",
    "created_at"
])
def test_re_mandatory_fields_missing(test_session, base_event, base_reward, field):
    """Ensure mandatory fields cannot be NULL."""
    kwargs = {
        "reward_event_key": "key1",
        "event_id": base_event.id,
        "reward_id": base_reward.id,
        "availability": "inshop",
        "price": 0,
        "created_by": "tester",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    kwargs[field] = None
    re = RewardEvent(**kwargs)
    test_session.add(re)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.commit()


# --- Nullable fields ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.reward_event
def test_re_accepts_null_optional_fields(test_session, base_event, base_reward):
    """Ensure nullable fields can be NULL."""
    re = RewardEvent(
        reward_event_key="key2",
        event_id=base_event.id,
        reward_id=base_reward.id,
        availability="inshop",
        price=0,
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat(),
        modified_by=None,
        modified_at=None
    )
    test_session.add(re)
    test_session.commit()

    assert re.modified_by is None
    assert re.modified_at is None


# --- Forced-NULL ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.reward_event
def test_availability_column_is_not_nullable(test_session, base_event, base_reward):
    """availability should not be nullable."""
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.execute(text(f"""
            INSERT INTO reward_events (reward_event_key, event_id, reward_id, availability, price, created_by, created_at)
            VALUES ('null_availability', {base_event.id}, {base_reward.id}, NULL, 0, 'tester', '{datetime.now(timezone.utc).isoformat()}')
        """))
        test_session.commit()


@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.reward_event
def test_price_column_is_not_nullable(test_session, base_event, base_reward):
    """price should not be nullable."""
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.execute(text(f"""
            INSERT INTO reward_events (reward_event_key, event_id, reward_id, availability, price, created_by, created_at)
            VALUES ('null_price', {base_event.id}, {base_reward.id}, 'inshop', NULL, 'tester', '{datetime.now(timezone.utc).isoformat()}')
        """))
        test_session.commit()
        

# --- Defaults ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.reward_event
def test_defaults_are_applied(test_session, base_event, base_reward):
    """Ensure default values are applied when omitted."""
    re = RewardEvent(
        reward_event_key="key3",
        event_id=base_event.id,
        reward_id=base_reward.id,
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(re)
    test_session.commit()

    assert re.availability == "inshop"
    assert re.price == 0


# --- Unique key ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.reward_event
def test_unique_reward_event_key(test_session, base_reward_event):
    """Ensure reward_event_key must be unique."""
    re2 = RewardEvent(
        reward_event_key=base_reward_event.reward_event_key,  # duplicate
        event_id=base_reward_event.event_id,
        reward_id=base_reward_event.reward_id,
        availability="onaction",
        price=0,
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(re2)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.commit()


# --- Composite unique ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.reward_event
def test_unique_event_reward_availability_combo(test_session, base_reward_event):
    """Ensure (event_id, reward_id, availability) must be unique."""
    re2 = RewardEvent(
        reward_event_key="combo2",
        event_id=base_reward_event.event_id,
        reward_id=base_reward_event.reward_id,
        availability=base_reward_event.availability,  # duplicate combo
        price=0,
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(re2)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.commit()


# --- FK CASCADE (event_id) ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.reward_event
def test_fk_cascade_on_event_delete(test_session, base_reward_event, base_event):
    """Deleting an Event cascades to RewardEvent."""
    assert test_session.query(RewardEvent).count() == 1

    # Delete Event
    test_session.delete(base_event)
    test_session.commit()

    assert test_session.query(RewardEvent).count() == 0


# --- FK CASCADE (reward_id) ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.reward_event
def test_fk_cascade_on_reward_delete(test_session, base_reward_event, base_reward):
    """Deleting a Reward cascades to RewardEvent."""
    assert test_session.query(RewardEvent).count() == 1

    # Delete Reward
    test_session.delete(base_reward)
    test_session.commit()

    assert test_session.query(RewardEvent).count() == 0
