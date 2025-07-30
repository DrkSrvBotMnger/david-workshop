import pytest
from bot.crud.actions_crud import create_action, get_action_by_key, get_all_actions, delete_action, get_action_by_id
from db.database import db_session
from datetime import datetime
from db.schema import Action


@pytest.fixture
def session():
    with db_session() as s:
        # Clear table to avoid interference
        s.query(Action).delete()
        s.commit()
        yield s


@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.action
def test_create_and_get_action(session):
    """Ensure action can be created and retrieved."""
    action_key = "test_action"
    create_action(
        session=session,
        action_key=action_key,
        description="Test action",
        default_self_reportable=True,
        input_fields_json='["url"]',
    )

    action = get_action_by_key(session, action_key)
    assert action is not None
    assert action.action_key == action_key


@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.action
def test_create_action_sets_timestamp(session):
    """create_action should set created_at automatically."""
    create_action(
        session=session,
        action_key="timestamp_test",
        description="Timestamp test",
        default_self_reportable=True
    )
    action = get_action_by_key(session, "timestamp_test")
    assert action is not None
    assert action.created_at is not None
    # Optionally check format
    assert len(action.created_at) >= 10

@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.action
def test_get_all_actions(session):
    """Ensure get_all_actions returns a list."""
    actions = get_all_actions(session)
    assert isinstance(actions, list)


@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.action
def test_delete_action(session):
    """Ensure delete_action removes action from DB."""
    action_key = "delete_me"
    create_action(
        session=session,
        action_key=action_key,
        description="Temp action",
        default_self_reportable=True
    )

    assert get_action_by_key(session, action_key) is not None
    deleted = delete_action(session, action_key)
    assert deleted is True
    assert get_action_by_key(session, action_key) is None


@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.action
def test_delete_action_returns_false_for_nonexistent(session):
    """delete_action should return False if no such action exists."""
    result = delete_action(session, "does_not_exist")
    assert result is False


@pytest.mark.crud
@pytest.mark.basic
@pytest.mark.action
def test_get_action_by_id(session):
    """get_action_by_id should retrieve the correct record."""
    create_action(
        session=session,
        action_key="id_lookup",
        description="Lookup by ID",
        default_self_reportable=True
    )
    action = get_action_by_key(session, "id_lookup")
    retrieved = get_action_by_id(session, action.id)
    assert retrieved is not None
    assert retrieved.action_key == "id_lookup"