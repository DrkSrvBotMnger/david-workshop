import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from bot.crud.actions_crud import create_action, get_action_by_key
from db.database import db_session
from db.schema import Action


@pytest.fixture
def session():
    with db_session() as s:
        # Clean table before each test
        s.query(Action).delete()
        s.commit()
        yield s


@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action
def test_action_key_required(session):
    """Action key must be provided (NOT NULL)."""
    with pytest.raises(IntegrityError):
        create_action(
            session=session,
            action_key=None,
            description="Missing key",
            input_fields_json=None
        )
        session.flush()
    session.rollback()


@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action
def test_action_key_unique(session):
    """Action key must be unique."""
    create_action(
        session=session,
        action_key="unique_test",
        description="First action"
    )

    with pytest.raises(IntegrityError):
        create_action(
            session=session,
            action_key="unique_test",  # duplicate
            description="Duplicate action"
        )
        session.flush()
    session.rollback()


@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action
def test_description_required(session):
    """Description must be provided (NOT NULL)."""
    with pytest.raises(IntegrityError):
        create_action(
            session=session,
            action_key="no_desc",
            description=None
        )
        session.flush()
    session.rollback()


@pytest.mark.schema
@pytest.mark.action
def test_input_fields_json_can_be_null(session):
    """input_fields_json can be left NULL."""
    create_action(
        session=session,
        action_key="null_fields",
        description="Null fields test"
    )
    action = get_action_by_key(session, "null_fields")
    assert action is not None
    assert action.input_fields_json is None


@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action
def test_created_at_required(session):
    """created_at must be provided (NOT NULL)."""
    with pytest.raises(IntegrityError):
        session.execute(text("""
            INSERT INTO actions (action_key, active, description)
            VALUES ('bad_created_at', True, 'Missing created_at')
        """))
        session.commit()


@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action
def test_active_required(session):
    """created_at must be provided (NOT NULL)."""
    with pytest.raises(IntegrityError):
        session.execute(text("""
            INSERT INTO actions (action_key, description, created_at)
            VALUES ('bad_active', 'Missing created_at', '2023-01-01T00:00:00')
        """))
        session.commit()