import pytest
import sqlalchemy.exc
import bot.crud
from datetime import datetime
from db.schema import EventLog


@pytest.mark.schema
@pytest.mark.basic
def test_eventlog_requires_action(test_session):
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        log = EventLog(
            event_id=None,
            action=None,
            performed_by="mod123",
            timestamp="2025-01-01T00:00:00"
        )
        test_session.add(log)
        test_session.commit()


@pytest.mark.schema
@pytest.mark.basic
def test_eventlog_requires_performed_by(test_session):
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        log = EventLog(
            event_id=None,
            action="delete",
            performed_by=None,
            timestamp="2025-01-01T00:00:00"
        )
        test_session.add(log)
        test_session.commit()


@pytest.mark.schema
@pytest.mark.basic
def test_eventlog_requires_timestamp(test_session):
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        log = EventLog(
            event_id=None,
            action="edit",
            performed_by="mod123",
            timestamp=None
        )
        test_session.add(log)
        test_session.commit()


@pytest.mark.schema
def test_eventlog_accepts_null_description(test_session):
    log = EventLog(
        event_id=None,
        action="create",
        performed_by="mod123",
        timestamp="2025-01-01T00:00:00",
        description=None
    )
    test_session.add(log)
    test_session.commit()

    assert log.description is None


@pytest.mark.schema
@pytest.mark.basic
def test_eventlog_event_id_set_null_on_delete(test_session):
    """Ensure that deleting an Event sets event_id to NULL in EventLog."""
    bot.crud.get_or_create_user(test_session, "9999", "SchemaTester")

    # Create event + update to generate logs
    bot.crud.create_event(
        session=test_session,
        event_id="constraint_evt",
        name="Constraint Test",
        type="test",
        description="Testing FK SET NULL",
        start_date="2025-01-01",
        end_date="2025-01-05",
        created_by="9999"
    )

    bot.crud.update_event(
        session=test_session,
        event_id="constraint_evt",
        modified_by="9999",
        modified_at=str(datetime.utcnow()),
        reason="Trigger log",
        name="Changed name"
    )

    bot.crud.delete_event(
        session=test_session,
        event_id="constraint_evt",
        deleted_by="9999",
        reason="Clean up"
    )

    logs = bot.crud.get_all_event_logs(test_session)
    assert len(logs) >= 2
    assert all(log.EventLog.event_id is None for log in logs)