import pytest
from db.database import db_session
from db.schema import Action
from bot.crud.actions_crud import create_action, get_action_by_key


@pytest.fixture
def session():
    with db_session() as s:
        # Clear table to avoid interference
        s.query(Action).delete()
        s.commit()
        yield s


@pytest.mark.crud
@pytest.mark.action
def test_create_action_accepts_null_input_fields(session):
    """create_action should allow input_fields_json=None."""
    create_action(
        session=session,
        action_key="null_test",
        description="Test null input fields",
        input_fields_json=None
    )
    action = get_action_by_key(session, "null_test")
    assert action is not None
    assert action.input_fields_json is None