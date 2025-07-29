import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from bot.commands.admin import AdminCommands

# --- Shared Fixtures / Helpers ---

def make_mock_event(**kwargs):
    """Helper to build a MagicMock event with sensible defaults."""
    event = MagicMock()
    event.visible = kwargs.get("visible", False)
    event.active = kwargs.get("active", False)
    event.embed_message_id = kwargs.get("embed_message_id", "456")
    event.name = kwargs.get("name", "Test Event")
    event.event_id = kwargs.get("event_id", "test_2025_08")
    event.role_id = kwargs.get("role_id", None)
    event.id = kwargs.get("id", 1)
    return event

def make_mock_interaction():
    """Helper to build a mock Interaction with async followup/send/defer."""
    inter = AsyncMock()
    inter.user.id = "123"

    # followup.send is async
    inter.followup.send = AsyncMock()

    # response.defer is async
    inter.response.defer = AsyncMock()

    # Guild + channel mocking
    mock_channel = MagicMock()
    mock_channel.send = AsyncMock()  # async send method

    inter.guild = MagicMock()
    inter.guild.get_channel = MagicMock(return_value=mock_channel)

    return inter


# --- ACTIVATE EVENT TESTS ---

@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.asyncio
async def test_activate_event_success_sets_active_and_sends_message():
    mock_interaction = make_mock_interaction()
    mock_event = make_mock_event(active=False, visible=False)

    with patch("bot.crud.get_event", return_value=mock_event), \
         patch("bot.crud.log_event_change") as mock_log, \
         patch("db.database.db_session") as mock_db:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminCommands(bot=None)
        await admin_cmds.activate_event.callback(admin_cmds, mock_interaction, mock_event.event_id)

        assert mock_event.active is True
        mock_interaction.followup.send.assert_called()
        mock_log.assert_called_once()


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.asyncio
async def test_activate_event_auto_sets_visible_if_not_visible():
    """Activate event should automatically set visible=True if it was not already visible."""
    mock_interaction = make_mock_interaction()
    mock_event = make_mock_event(active=False, visible=False)  # not visible initially

    with patch("bot.crud.get_event", return_value=mock_event), \
         patch("bot.crud.log_event_change"), \
         patch("db.database.db_session") as mock_db:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminCommands(bot=None)
        await admin_cmds.activate_event.callback(admin_cmds, mock_interaction, mock_event.event_id)

        # Must now be both active and visible
        assert mock_event.active is True
        assert mock_event.visible is True


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.asyncio
async def test_activate_event_sets_modified_by_and_modified_at():
    mock_interaction = make_mock_interaction()
    mock_event = make_mock_event(active=False, visible=True)

    with patch("bot.crud.get_event", return_value=mock_event), \
         patch("bot.crud.log_event_change"), \
         patch("db.database.db_session") as mock_db:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminCommands(bot=None)
        await admin_cmds.activate_event.callback(admin_cmds, mock_interaction, mock_event.event_id)

        assert mock_event.modified_by == "123"
        assert isinstance(datetime.fromisoformat(mock_event.modified_at), datetime)


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.asyncio
async def test_activate_event_creates_log_entry():
    mock_interaction = make_mock_interaction()
    mock_event = make_mock_event(active=False, visible=True)

    with patch("bot.crud.get_event", return_value=mock_event), \
         patch("bot.crud.log_event_change") as mock_log, \
         patch("db.database.db_session") as mock_db:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminCommands(bot=None)
        await admin_cmds.activate_event.callback(admin_cmds, mock_interaction, mock_event.event_id)

        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert kwargs["action"] == "edit"
        assert kwargs["performed_by"] == "123"
        assert "marked as active" in kwargs["description"]


# --- DEACTIVATE EVENT TESTS ---

@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.asyncio
async def test_deactivate_event_success_sets_inactive_and_sends_message():
    mock_interaction = make_mock_interaction()
    mock_event = make_mock_event(active=True, visible=True)

    with patch("bot.crud.get_event", return_value=mock_event), \
         patch("bot.crud.log_event_change") as mock_log, \
         patch("db.database.db_session") as mock_db:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminCommands(bot=None)
        await admin_cmds.deactivate_event.callback(admin_cmds, mock_interaction, mock_event.event_id)

        assert mock_event.active is False
        mock_interaction.followup.send.assert_called()
        mock_log.assert_called_once()


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.asyncio
async def test_deactivate_event_sets_modified_by_and_modified_at():
    mock_interaction = make_mock_interaction()
    mock_event = make_mock_event(active=True, visible=True)

    with patch("bot.crud.get_event", return_value=mock_event), \
         patch("bot.crud.log_event_change"), \
         patch("db.database.db_session") as mock_db:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminCommands(bot=None)
        await admin_cmds.deactivate_event.callback(admin_cmds, mock_interaction, mock_event.event_id)

        assert mock_event.modified_by == "123"
        assert isinstance(datetime.fromisoformat(mock_event.modified_at), datetime)


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.asyncio
async def test_deactivate_event_creates_log_entry():
    mock_interaction = make_mock_interaction()
    mock_event = make_mock_event(active=True, visible=True)

    with patch("bot.crud.get_event", return_value=mock_event), \
         patch("bot.crud.log_event_change") as mock_log, \
         patch("db.database.db_session") as mock_db:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminCommands(bot=None)
        await admin_cmds.deactivate_event.callback(admin_cmds, mock_interaction, mock_event.event_id)

        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert kwargs["action"] == "edit"
        assert kwargs["performed_by"] == "123"
        assert "marked as inactive" in kwargs["description"]
