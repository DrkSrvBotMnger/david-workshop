import pytest
from datetime import datetime, timezone
import sqlalchemy.exc
from sqlalchemy import text
from db.schema import Action


# --- Mandatory fields ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action
@pytest.mark.parametrize("field", [
    "action_key",
    "action_description",
    "created_at"
])
def test_a_mandatory_fields_missing(test_session, field):
    """Ensure mandatory fields cannot be NULL."""
    kwargs = {
        "action_key": None,
        "is_active": True,
        "action_description": "tester",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    kwargs[field] = None
    a = Action(**kwargs)
    test_session.add(a)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.commit()
        

# --- Nullable fields ---
@pytest.mark.schema
@pytest.mark.action
def test_a_accepts_null_optional_fields(test_session):
    """input_fields_json and deactivated_at should be nullable."""
    a = Action(
        action_key="null_optional_fields_act",
        is_active=True,
        action_description="test",
        created_at=datetime.now(timezone.utc).isoformat(),
        input_fields_json=None,
        deactivated_at=None
    )
    test_session.add(a)
    test_session.commit()

    assert a.input_fields_json is None
    assert a.deactivated_at is None
    

# --- Forced-NULL ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action
@pytest.mark.asyncio 
async def test_is_active_column_is_not_nullable(test_session): 
    """is_active should not be nullable."""
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.execute(text(""" INSERT INTO actions (action_key, is_active, action_description, created_at) VALUES ('aid', NULL, 'null_is_active_act', '2025-08-03T03:00:00.000000')"""))
        test_session.commit()

# --- Defaults ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action
def test_action_default_value_is_correct(test_session):
    """Ensure Action default for is_active is True."""
    a = Action(
        action_key="default_action",
        action_description="Test action defaults",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(a)
    test_session.commit()

    assert a.is_active is True


# --- Unique key ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action
def test_action_key_unique_constraint(test_session, base_action):
    """Ensure action_key must be unique at the DB level."""
    action2 = Action(
        action_key=base_action.action_key,
        is_active=True,
        action_description="test",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(action2)

    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.commit()