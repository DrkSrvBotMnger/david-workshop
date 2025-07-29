import pytest
import sqlalchemy.exc
from sqlalchemy import text
import bot.crud


# This user will be used for all tests
@pytest.fixture
def default_user(test_session):
    return bot.crud.get_or_create_user(test_session, "required_check", "RequiredTester")

# Helper function to avoid code duplication
def _expect_event_creation_failure(test_session, **override_fields):
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        bot.crud.create_event(
            session=test_session,
            event_id=override_fields.get("event_id", "missing_field_evt"),
            name=override_fields.get("name", "Missing Field Test"),
            type=override_fields.get("type", "test"),
            description=override_fields.get("description", "Testing required fields"),
            start_date=override_fields.get("start_date", "2025-01-01"),
            created_by=override_fields.get("created_by", "required_check")
        )
        test_session.commit()


@pytest.mark.schema
@pytest.mark.basic
def test_event_requires_event_id(test_session, default_user):
    _expect_event_creation_failure(test_session, event_id=None)


@pytest.mark.schema
@pytest.mark.basic
def test_event_requires_name(test_session, default_user):
    _expect_event_creation_failure(test_session, name=None)


@pytest.mark.schema
@pytest.mark.basic
def test_event_requires_type(test_session, default_user):
    _expect_event_creation_failure(test_session, type=None)


@pytest.mark.schema
@pytest.mark.basic
def test_event_requires_description(test_session, default_user):
    _expect_event_creation_failure(test_session, description=None)


@pytest.mark.schema
@pytest.mark.basic
def test_event_requires_start_date(test_session, default_user):
    _expect_event_creation_failure(test_session, start_date=None)


@pytest.mark.schema
@pytest.mark.basic
def test_event_requires_created_by(test_session, default_user):
    _expect_event_creation_failure(test_session, created_by=None)


@pytest.mark.schema
@pytest.mark.basic
@pytest.mark.asyncio 
async def test_priority_column_is_not_nullable(test_session): 
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        test_session.execute(text(""" INSERT INTO events ( event_id, name, type, description, start_date, created_by ) VALUES ('eid', 'null_priority_evt', 'typ','should fail','2025-01-01','test user')"""))
        test_session.commit()


@pytest.mark.schema
def test_event_accepts_null_optional_fields(test_session):
    """end_date should be nullable (for ongoing events)."""
    bot.crud.get_or_create_user(test_session, "null1", "Tester")
    event = bot.crud.create_event(
        session=test_session,
        event_id="evt_null_end",
        name="No End Date",
        type="test",
        description="Ongoing event",
        start_date="2025-01-01",
        end_date=None,
        priority=0,
        shop_section_id=None,
        tags=None,
        embed_channel_id=None,
        embed_message_id=None,
        role_id=None,
        created_by="null1"
    )
    assert event.end_date is None


@pytest.mark.schema
@pytest.mark.basic
def test_event_id_unique_constraint(test_session):
    """Ensure event_id must be unique at the DB level."""
    bot.crud.get_or_create_user(test_session, "u1", "UniqTester")

    bot.crud.create_event(
        session=test_session,
        event_id="dupe_event",
        name="Original",
        type="test",
        description="Testing unique constraint",
        start_date="2025-01-01",
        end_date="2025-01-02",
        created_by="u1"
    )

    with pytest.raises(sqlalchemy.exc.IntegrityError):
        bot.crud.create_event(
            session=test_session,
            event_id="dupe_event",  # Should conflict
            name="Duplicate",
            type="test",
            description="Should fail",
            start_date="2025-01-03",
            end_date="2025-01-04",
            created_by="u1"
        )
        test_session.commit()