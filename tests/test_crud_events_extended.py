import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import datetime
from db.schema import EventLog
import bot.crud
import sqlalchemy.exc


# --- Extended tests for event CRUD ---
def test_create_event_with_optional_fields(test_session):
    bot.crud.get_or_create_user(test_session, "1234", "OptionalMod") 
    event = bot.crud.create_event(
        session=test_session,
        event_id="opt_event",
        name="Optional Fields Test",
        type="custom",
        description="Testing optional fields.",
        start_date="2025-01-01",
        end_date=None,
        created_by="1234",
        coordinator_id="mod456",
        tags="test,optional",
        priority=2,
        shop_section_id="shop1",
        active=False,
        visible=False,
        embed_channel_id=1234567890,
        embed_message_id=None,
        role_id=None
    )
    
    assert event.end_date is None
    assert event.coordinator_id == "mod456"
    assert event.tags == "test,optional"
    assert event.priority == 2
    assert event.shop_section_id == "shop1"
    assert event.visible is False
    assert event.active is False
    assert event.embed_channel_id == 1234567890
    assert event.embed_message_id is None
    assert event.role_id is None


def test_event_creation_timestamps(test_session):
    bot.crud.get_or_create_user(test_session, "1234", "TimeCheck")
    event = bot.crud.create_event(
        session=test_session,
        event_id="time_evt",
        name="Time Event",
        type="test",
        description="Testing timestamps",
        start_date="2025-01-01",
        end_date="2025-01-02",
        created_by="1234"
    )

    assert event.created_at is not None
    assert isinstance(event.created_at, str)
    assert event.modified_at is None  # Initially unset


def test_update_event_tags_and_priority(test_session, seed_user_and_event):
    seed_user_and_event(test_session)
    bot.crud.update_event(
        session=test_session,
        event_id="test_event",
        modified_by="9999",
        modified_at=str(datetime.utcnow()),
        tags="updated,tags",
        priority=5,
    )
    updated = bot.crud.get_event(test_session, "test_event")
    assert updated.tags == "updated,tags"
    assert updated.priority == 5


def test_update_event_clears_tags(test_session, seed_user_and_event):
    seed_user_and_event(test_session)
    # Simulate clearing tags
    bot.crud.update_event(
        session=test_session,
        event_id="test_event",
        modified_by="mod-clear",
        modified_at=str(datetime.utcnow()),
        tags=None
    )

    updated = bot.crud.get_event(test_session, "test_event")
    assert updated.tags is None


def test_update_nonexistent_event_returns_none(test_session):
    result = bot.crud.update_event(
        session=test_session,
        event_id="ghost_event",
        modified_by="modx",
        modified_at=str(datetime.utcnow()),
        name="Should Fail"
    )
    assert result is None


def test_update_event_logs_reason(test_session, seed_user_and_event):
    seed_user_and_event(test_session)

    reason = "Fixing event name typo"
    modified_at = str(datetime.utcnow())

    bot.crud.update_event(
        session=test_session,
        event_id="test_event",
        modified_by="mod789",
        modified_at=modified_at,
        reason=reason,
        name="Fixed Name"
    )

    logs = bot.crud.get_all_event_logs(test_session)
    edit_logs = [log.EventLog for log in logs if log.EventLog.action == "edit"]

    assert len(edit_logs) >= 1
    assert any(reason in log.description for log in edit_logs)


def test_delete_nonexistent_event_returns_false(test_session):
    deleted = bot.crud.delete_event(
        session=test_session,
        event_id="not_here",
        deleted_by="modx",
        reason="Testing bad delete"
    )
    assert deleted is False


def test_delete_event_logs_reason(test_session, seed_user_and_event):
    seed_user_and_event(test_session)

    reason = "Event cancelled"
    deleted = bot.crud.delete_event(
        session=test_session,
        event_id="test_event",
        deleted_by="mod456",
        reason=reason
    )
    assert deleted is True

    logs = bot.crud.get_all_event_logs(test_session)
    delete_logs = [log.EventLog for log in logs if log.EventLog.action == "delete"]

    assert len(delete_logs) >= 1
    assert any(reason in log.description for log in delete_logs)


def test_filter_events_by_tag(test_session):
    bot.crud.get_or_create_user(test_session, "1234", "TagMod")

    # Create 3 events with different tags
    bot.crud.create_event(
        session=test_session,
        event_id="tagged1",
        name="Event One",
        type="test",
        description="Tag A",
        start_date="2025-01-01",
        end_date="2025-01-05",
        created_by="1234",
        tags="darklina, week"
    )
    bot.crud.create_event(
        session=test_session,
        event_id="tagged2",
        name="Event Two",
        type="test",
        description="Tag B",
        start_date="2025-01-06",
        end_date="2025-01-10",
        created_by="1234",
        tags="exchange"
    )
    bot.crud.create_event(
        session=test_session,
        event_id="tagged3",
        name="Event Three",
        type="test",
        description="Tag C",
        start_date="2025-01-11",
        end_date="2025-01-15",
        created_by="1234",
        tags="hello, darklina, bingo"
    )

    # Now filter with tag = "darklina"
    filtered = bot.crud.get_all_events(test_session, tag="darklina")

    assert len(filtered) == 2
    assert all("darklina" in e.tags for e in filtered)


def test_filter_tags_with_spaces_in_commas(test_session):
    bot.crud.get_or_create_user(test_session, "1234", "TagMatchMod")

    bot.crud.create_event(
        session=test_session,
        event_id="spaced_tags",
        name="Event with Spaced Tags",
        type="test",
        description="Testing spaced comma tags",
        start_date="2025-01-01",
        end_date="2025-01-02",
        created_by="1234",
        tags="darklina, week, bingo"
    )

    # Search for tag that has leading space in original string
    filtered = bot.crud.get_all_events(test_session, tag="week")
    assert any(e.event_id == "spaced_tags" for e in filtered)


def test_filter_events_by_visibile(test_session):
    bot.crud.get_or_create_user(test_session, "1234", "ModVisible")

    # One visible, one not
    bot.crud.create_event(
        session=test_session,
        event_id="vis1",
        name="Visible",
        type="test",
        description="Visible event",
        start_date="2025-01-01",
        end_date="2025-01-02",
        created_by="1234",
        visible=True
    )
    bot.crud.create_event(
        session=test_session,
        event_id="vis2",
        name="Hidden",
        type="test",
        description="Hidden event",
        start_date="2025-01-03",
        end_date="2025-01-04",
        created_by="1234",
        visible=False
    )

    filtered = bot.crud.get_all_events(test_session, visible=True)
    assert len(filtered) == 1
    assert filtered[0].name == "Visible"


def test_filter_events_by_active(test_session):
    bot.crud.get_or_create_user(test_session, "1234", "ModActive")

    # One active, one not
    bot.crud.create_event(
        session=test_session,
        event_id="act1",
        name="Active",
        type="test",
        description="Active event",
        start_date="2025-01-01",
        end_date="2025-01-02",
        created_by="1234",
        active=True
    )
    bot.crud.create_event(
        session=test_session,
        event_id="act2",
        name="Inactive",
        type="test",
        description="Inactive event",
        start_date="2025-01-03",
        end_date="2025-01-04",
        created_by="1234",
        active=False
    )

    filtered = bot.crud.get_all_events(test_session, active=True)
    assert len(filtered) == 1
    assert filtered[0].name == "Active"


def test_filter_events_by_mod_id(test_session):
    # Create a user (creator)
    bot.crud.get_or_create_user(test_session, "creator123", "CreatorUser")
    bot.crud.get_or_create_user(test_session, "mod999", "EditorUser")

    # Create 2 events
    bot.crud.create_event(
        session=test_session,
        event_id="by_creator",
        name="By Creator",
        type="test",
        description="Made by creator123",
        start_date="2025-01-01",
        end_date="2025-01-05",
        created_by="creator123"
    )

    bot.crud.create_event(
        session=test_session,
        event_id="by_editor",
        name="By Editor",
        type="test",
        description="Modified by mod999",
        start_date="2025-01-06",
        end_date="2025-01-10",
        created_by="creator123"
    )

    # Update second event (sets modified_by)
    bot.crud.update_event(
        session=test_session,
        event_id="by_editor",
        modified_by="mod999",
        modified_at=str(datetime.utcnow()),
        reason="Test edit",
        name="Editor Modified"
    )

    # Filter by mod_id (should match both creator and modifier logic)
    filtered_creator = bot.crud.get_all_events(test_session, mod_id="creator123")
    filtered_editor = bot.crud.get_all_events(test_session, mod_id="mod999")

    assert any(e.event_id == "by_creator" for e in filtered_creator)
    assert any(e.event_id == "by_editor" for e in filtered_editor)


def test_filter_event_logs_by_action(test_session, seed_user_and_event):
    seed_user_and_event(test_session)
    bot.crud.update_event(
        session=test_session,
        event_id="test_event",
        modified_by="admin999",
        modified_at=str(datetime.utcnow()),
        name="Log Filter Test"
    )

    logs = bot.crud.get_all_event_logs(test_session, action="edit")
    assert len(logs) == 1
    assert logs[0].EventLog.action == "edit"


def test_filter_event_logs_by_moderator(test_session, seed_user_and_event):
    seed_user_and_event(test_session)

    bot.crud.update_event(
        session=test_session,
        event_id="test_event",
        modified_by="mod999",
        modified_at=str(datetime.utcnow()),
        reason="Update for log test",
        name="Updated Title"
    )

    logs_all = bot.crud.get_all_event_logs(test_session)
    logs_by_mod = bot.crud.get_all_event_logs(test_session, moderator="mod999")
    logs_by_fake = bot.crud.get_all_event_logs(test_session, moderator="ghost")

    assert any(log.EventLog.performed_by == "mod999" for log in logs_by_mod)
    assert len(logs_by_fake) == 0
    assert len(logs_by_mod) <= len(logs_all)  # Should be a subset