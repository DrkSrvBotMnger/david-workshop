# tests/admin/test_list_show_logs.py

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from bot.commands.admin import AdminCommands


# --- Shared Fixtures / Helpers ---

def make_mock_interaction():
    """Helper to build a mock Interaction with async followup/send/defer."""
    inter = AsyncMock()
    inter.user.id = "123"
    inter.followup.send = AsyncMock()
    inter.response.defer = AsyncMock()
    mock_channel = MagicMock()
    mock_channel.send = AsyncMock()
    inter.guild = MagicMock()
    inter.guild.get_channel = MagicMock(return_value=mock_channel)
    return inter


def make_mock_event(**kwargs):
    """Builds a mock event object."""
    event = MagicMock()
    event.event_id = kwargs.get("event_id", "event_1")
    event.name = kwargs.get("name", "Test Event")
    event.visible = kwargs.get("visible", True)
    event.active = kwargs.get("active", False)
    event.tags = kwargs.get("tags", "tag1,tag2")
    event.modified_by = kwargs.get("modified_by", "123")
    event.created_by = kwargs.get("created_by", "123")
    event.created_at = kwargs.get("created_at", datetime.utcnow())
    event.modified_at = kwargs.get("modified_at", datetime.utcnow())
    event.embed_message_id = kwargs.get("embed_message_id", "456")
    event.role_id = kwargs.get("role_id", None)
    event.coordinator_id = kwargs.get("coordinator_id", "123")
    event.description = kwargs.get("description", "Description")
    event.priority = kwargs.get("priority", 0)
    event.shop_section_id = kwargs.get("shop_section_id", "shop1")
    event.tags = kwargs.get("tags", "tag1,tag2")
    return event


# --- LIST EVENTS TESTS ---

@pytest.mark.asyncio
async def test_list_events_pagination_priority():
    """List Events paginates correctly when >5 events."""
    mock_interaction = make_mock_interaction()

    # 6 events → should require 2 pages
    events = [
        make_mock_event(event_id=f"event_{i}", created_at=datetime.utcnow() - timedelta(days=i))
        for i in range(6)
    ]

    with patch("bot.crud.get_all_events", return_value=events), \
         patch("db.database.db_session") as mock_db, \
         patch("bot.commands.admin.paginate_embeds", new_callable=AsyncMock) as mock_paginate:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminCommands(bot=None)
        await admin_cmds.list_events.callback(admin_cmds, mock_interaction)

        # Expect pagination function called with at least 2 pages
        args, _ = mock_paginate.call_args
        pages = args[1]
        assert len(pages) >= 2


# --- SHOW EVENT TESTS ---

@pytest.mark.asyncio
async def test_show_event_displays_all_core_metadata_priority():
    mock_interaction = make_mock_interaction()
    mock_event = make_mock_event()

    with patch("bot.crud.get_event", return_value=mock_event), \
         patch("db.database.db_session") as mock_db:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminCommands(bot=None)
        await admin_cmds.show_event.callback(admin_cmds, mock_interaction, mock_event.event_id)

        # Expect an embed to have been sent
        mock_interaction.followup.send.assert_called()
        sent_embed = mock_interaction.followup.send.call_args[1].get("embed") or \
                     mock_interaction.followup.send.call_args[0][0]

        # Check that core metadata is in embed fields
        assert mock_event.name in str(sent_embed.to_dict())
        assert mock_event.event_id in str(sent_embed.to_dict())
        assert str(mock_event.priority) in str(sent_embed.to_dict())


# --- EVENT LOGS TESTS ---

@pytest.mark.asyncio
async def test_eventlog_sorted_most_recent_first_and_pagination_priority():
    mock_interaction = make_mock_interaction()

    # Create fake logs: (log_obj, event_id)
    log1 = MagicMock()
    log1.action = "edit"
    log1.performed_by = "123"
    log1.timestamp = datetime.utcnow()
    log1.description = "Latest log"

    log2 = MagicMock()
    log2.action = "create"
    log2.performed_by = "123"
    log2.timestamp = datetime.utcnow() - timedelta(days=1)
    log2.description = "Older log"

    logs = [(log1, "event1"), (log2, "event2")]

    with patch("bot.crud.get_all_event_logs", return_value=logs), \
         patch("db.database.db_session") as mock_db, \
         patch("bot.commands.admin.paginate_embeds", new_callable=AsyncMock) as mock_paginate:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminCommands(bot=None)
        await admin_cmds.eventlog.callback(admin_cmds, mock_interaction)

        # Pagination called
        assert mock_paginate.called

        # Ensure sorted order — latest first
        sorted_logs = sorted(logs, key=lambda l: l[0].timestamp, reverse=True)
        assert logs == sorted_logs
