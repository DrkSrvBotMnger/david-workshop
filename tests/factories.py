import pytest
from datetime import datetime, timezone
from db.schema import Action, ActionEvent, Event, EventStatus, Reward, RewardEvent


@pytest.fixture
def base_event(test_session):
    """Create a base Event for FK testing."""
    event = Event(
        event_key="test_event",
        event_name="Test Event",
        event_type="test",
        event_description="Test event",
        start_date="2025-01-01",
        priority=0,
        event_status=EventStatus.draft,
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(event)
    test_session.flush()
    return event


@pytest.fixture
def active_event(test_session):
    event = Event(
        event_key="test_event_active",
        event_name="Test Event",
        event_type="test",
        event_description="desc",
        start_date="2025-01-01",
        event_status=EventStatus.active,
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(event)
    test_session.flush()
    return event


@pytest.fixture
def base_action(test_session):
    """Create a base Action for FK testing."""
    action = Action(
        action_key="test_action",
        is_active=True,
        action_description="Test action",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(action)
    test_session.flush()
    return action


@pytest.fixture
def base_action_event(test_session, base_event, base_action):
    """Create a base ActionEvent for FK testing."""
    action_event = ActionEvent(
        action_event_key="test_action_event",
        action_id=base_action.id,
        event_id=base_event.id,
        variant="default",
        points_granted=0,
        is_allowed_during_visible=False,
        is_self_reportable=True,
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(action_event)
    test_session.flush()
    return action_event
    

@pytest.fixture
def base_reward(test_session):
    """Create a base Reward for base RewardEvent."""
    reward = Reward(
        reward_key="test_reward_event",
        reward_type="test",
        reward_name="Test Reward",
        is_released_on_active=False,
        is_stackable=False,
        number_granted=0,
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(reward)
    test_session.flush()
    return reward
    

@pytest.fixture
def base_reward_event(test_session, base_event, base_reward):
    """Create a base RewardEvent for FK testing."""
    reward_event = RewardEvent(
        reward_event_key="test_reward_event",
        event_id=base_event.id,
        reward_id=base_reward.id,
        availability="inshop",
        price=0,
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(reward_event)
    test_session.flush()
    return reward_event