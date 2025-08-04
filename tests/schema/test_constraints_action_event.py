import pytest
import sqlalchemy.exc
from sqlalchemy import text
from datetime import datetime, timezone
from db.schema import ActionEvent


# --- Mandatory fields ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action_event
@pytest.mark.parametrize("field", [
    "action_event_key",
    "action_id",
    "event_id",
    "variant",
    "created_by",
    "created_at"
])
def test_ae_mandatory_fields_missing(test_session, base_action, base_event, field):
    """Ensure mandatory fields cannot be NULL."""
    kwargs = {
        "action_event_key": "key1",
        "action_id": base_action.id,
        "event_id": base_event.id,
        "variant": "default",
        "points_granted": 0,
        "is_allowed_during_visible": False,
        "is_self_reportable": True,
        "created_by": "tester",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    kwargs[field] = None
    ae = ActionEvent(**kwargs)
    test_session.add(ae)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.commit()


# --- Nullable fields ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action_event
def test_actionevent_accepts_null_optional_fields(test_session, base_action, base_event):
    """Ensure nullable fields can be NULL."""
    ae = ActionEvent(
        action_event_key="key2",
        action_id=base_action.id,
        event_id=base_event.id,
        variant="default",
        points_granted=0,
        reward_event_id=None,
        is_allowed_during_visible=False,
        is_self_reportable=True,
        input_help_text=None,
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat(),
        modified_by=None,
        modified_at=None
    )
    test_session.add(ae)
    test_session.commit()

    assert ae.reward_event_id is None
    assert ae.input_help_text is None
    assert ae.modified_by is None
    assert ae.modified_at is None


# --- Forced-NULL ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action_event
def test_points_granted_column_is_not_nullable(test_session, base_action, base_event):
    """points_granted should not be nullable."""
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.execute(text(f"""
            INSERT INTO action_events (action_event_key, action_id, event_id, variant, points_granted, is_allowed_during_visible, is_self_reportable, created_by, created_at)
            VALUES ('null_points', {base_action.id}, {base_event.id}, 'default', NULL, False, True, 'tester', '{datetime.now(timezone.utc).isoformat()}')
        """))
        test_session.commit()


@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action_event
def test_is_allowed_during_visible_column_is_not_nullable(test_session, base_action, base_event):
    """is_allowed_during_visible should not be nullable."""
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.execute(text(f"""
            INSERT INTO action_events (action_event_key, action_id, event_id, variant, points_granted, is_allowed_during_visible, is_self_reportable, created_by, created_at)
            VALUES ('null_allowed_visible', {base_action.id}, {base_event.id}, 'default', 0, NULL, True, 'tester', '{datetime.now(timezone.utc).isoformat()}')
        """))
        test_session.commit()


@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action_event
def test_is_self_reportable_column_is_not_nullable(test_session, base_action, base_event):
    """is_self_reportable should not be nullable."""
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.execute(text(f"""
            INSERT INTO action_events (action_event_key, action_id, event_id, variant, points_granted, is_allowed_during_visible, is_self_reportable, created_by, created_at)
            VALUES ('null_self_reportable', {base_action.id}, {base_event.id}, 'default', 0, False, NULL, 'tester', '{datetime.now(timezone.utc).isoformat()}')
        """))
        test_session.commit()


# --- Defaults ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action_event
def test_defaults_are_applied(test_session, base_action, base_event):
    """Ensure default values are applied when omitted."""
    ae = ActionEvent(
        action_event_key="key3",
        action_id=base_action.id,
        event_id=base_event.id,
        variant="default",
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(ae)
    test_session.commit()

    assert ae.points_granted == 0
    assert ae.is_allowed_during_visible is False
    assert ae.is_self_reportable is True


# --- Unique key ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action_event
def test_unique_action_event_key(test_session, base_action_event):
    """Ensure action_event_key must be unique."""
    ae2 = ActionEvent(
        action_event_key=base_action_event.action_event_key,  # duplicate
        action_id=base_action_event.action_id,
        event_id=base_action_event.event_id,
        variant="default2",
        points_granted=0,
        is_allowed_during_visible=False,
        is_self_reportable=True,
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(ae2)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.commit()


# --- Composite unique ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action_event
def test_unique_event_action_variant_combo(test_session, base_action_event):
    """Ensure (event_id, action_id, variant) must be unique."""
    ae2 = ActionEvent(
        action_event_key="combo2",
        action_id=base_action_event.action_id,
        event_id=base_action_event.event_id,
        variant=base_action_event.variant,
        points_granted=0,
        is_allowed_during_visible=False,
        is_self_reportable=True,
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(ae2)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.commit()


# --- FK CASCADE (action_id) ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action_event
def test_fk_cascade_on_action_delete(test_session, base_action, base_event):
    """Deleting an Action cascades to ActionEvent."""
    ae = ActionEvent(
        action_event_key="cascade_action",
        action_id=base_action.id,
        event_id=base_event.id,
        variant="default",
        points_granted=0,
        is_allowed_during_visible=False,
        is_self_reportable=True,
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(ae)
    test_session.flush()

    # Delete Action
    test_session.delete(base_action)
    test_session.commit()

    assert test_session.query(ActionEvent).count() == 0


# --- FK CASCADE (event_id) ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action_event
def test_fk_cascade_on_event_delete(test_session, base_action, base_event):
    """Deleting an Event cascades to ActionEvent."""
    ae = ActionEvent(
        action_event_key="cascade_event",
        action_id=base_action.id,
        event_id=base_event.id,
        variant="default",
        points_granted=0,
        is_allowed_during_visible=False,
        is_self_reportable=True,
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(ae)
    test_session.flush()

    # Delete Event
    test_session.delete(base_event)
    test_session.commit()

    assert test_session.query(ActionEvent).count() == 0
    

# --- FK SET NULL (reward_event_id) ---
@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.action_event
def test_fk_set_null_on_reward_event_delete(test_session, base_action, base_event, base_reward_event):
    """Deleting a RewardEvent sets reward_event_id to NULL in ActionEvent."""
    ae = ActionEvent(
        action_event_key="setnull_reward",
        action_id=base_action.id,
        event_id=base_event.id,
        reward_event_id=base_reward_event.id,
        variant="default",
        points_granted=0,
        is_allowed_during_visible=False,
        is_self_reportable=True,
        created_by="tester",
        created_at=datetime.now(timezone.utc).isoformat()
    )
    test_session.add(ae)
    test_session.flush()

    # Delete RewardEvent
    test_session.delete(base_reward_event)
    test_session.commit()

    saved = test_session.query(ActionEvent).filter_by(action_event_key="setnull_reward").first()
    assert saved.reward_event_id is None