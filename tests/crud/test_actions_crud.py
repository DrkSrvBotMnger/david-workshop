import pytest
import sqlalchemy.exc
from datetime import datetime, timezone
from db.schema import Action, ActionEvent
from bot.crud import actions_crud


# --- CREATE ---
@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.action
def test_create_action_full_dict(test_session):
    """Create action with full dict data."""
    data = {
        "action_key": "crud_action_full",
        "action_description": "Full Dict Action"
    }
    action = actions_crud.create_action(test_session, data)
    test_session.commit()

    assert action.id is not None
    assert action.action_key == "crud_action_full"
    assert action.created_at is not None


@pytest.mark.crud
@pytest.mark.action
def test_create_action_minimal_fields_defaults(test_session):
    """Create action with minimal fields and check defaults."""
    data = {
        "action_key": "crud_action_full",
        "action_description": "Full Dict Action"
    }
    action = actions_crud.create_action(test_session, data)
    test_session.commit()

    assert action.is_active is True
    

@pytest.mark.crud
@pytest.mark.action
def test_create_action_missing_required_key(test_session):
    """Creating an action without action_key should fail."""
    data = {
        "action_description": "No Key Action"
    }
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        actions_crud.create_action(test_session, data)
        test_session.commit()


# --- READ ---
@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.action
def test_get_action_by_key(test_session):
    """Fetch action by key."""
    action = Action(
        action_key="test_action",
        action_description="Test action description",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(action)
    test_session.commit()

    fetched = actions_crud.get_action_by_key(test_session, "test_action")
    assert fetched is not None
    assert fetched.action_key == "test_action"


@pytest.mark.crud
@pytest.mark.action
def test_get_all_actions_and_filters(test_session):
    """Ensure get_all_actions returns expected objects and filters work."""
    action1 = Action(
        action_key="search_me",
        action_description="desc",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    action2 = Action(
        action_key="other_action",
        action_description="desc",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add_all([action1, action2])
    test_session.commit()

    results = actions_crud.get_all_actions(test_session)
    assert action1 in results and action2 in results

    filtered = actions_crud.get_all_actions(test_session, key_search="search_me")
    assert all("search_me" in a.action_key for a in filtered)


# --- DELETE ---
@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.action
def test_delete_action_existing(test_session):
    """Delete existing action."""
    action = Action(
        action_key="delete_me",
        action_description="desc",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(action)
    test_session.commit()

    result = actions_crud.delete_action(test_session, "delete_me")
    test_session.commit()

    assert result is True
    assert test_session.query(Action).filter_by(action_key="delete_me").count() == 0


@pytest.mark.crud
@pytest.mark.action
def test_delete_action_non_existing(test_session):
    """Deleting missing action returns False."""
    result = actions_crud.delete_action(test_session, "no_such_action")
    assert result is False


# --- LINK TO ACTIVE EVENT ---
@pytest.mark.crud
@pytest.mark.action
def test_action_is_linked_to_active_event_true(test_session, base_action, active_event):
    """Link action to active event and verify detection."""
    link = ActionEvent(
        action_event_key="link_key",
        event_id=active_event.id,
        action_id=base_action.id,
        variant="default",
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(link)
    test_session.commit()

    assert actions_crud.action_is_linked_to_active_event(
        test_session,
        base_action.action_key
    ) is True


@pytest.mark.crud
@pytest.mark.reward
def test_action_is_linked_to_active_event_false(test_session, base_action):
    """No active event linked."""
    assert actions_crud.action_is_linked_to_active_event(test_session, base_action.action_key) is False