import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from bot.commands.admin.events_admin import AdminEventCommands

# --- Shared Fixtures / Helpers ---

def make_mock_event(**kwargs):
    """Helper to build a MagicMock event with sensible defaults."""
    event = MagicMock()
    event.visible = kwargs.get("visible", False)
    event.embed_message_id = kwargs.get("embed_message_id", "456")
    event.name = kwargs.get("name", "Test Event")
    event.event_id = kwargs.get("event_id", "test_2025_08")
    event.role_id = kwargs.get("role_id", None)
    event.id = kwargs.get("id", 1)
    event.active = kwargs.get("active", False)
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


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.asyncio
async def test_display_event_success_sets_visible_and_sends_message():
    mock_interaction = make_mock_interaction()
    mock_event = make_mock_event(visible=False)

    with patch("bot.crud.events_crud.get_event", return_value=mock_event), \
         patch("bot.crud.general_crud.log_change") as mock_log, \
         patch("db.database.db_session") as mock_db:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminEventCommands(bot=None)
        await admin_cmds.display_event.callback(admin_cmds, mock_interaction, mock_event.event_id)

        assert mock_event.visible is True
        mock_interaction.followup.send.assert_called_with(
            f"✅ Event `{mock_event.name} ({mock_event.event_id})` is now visible."
        )
        mock_log.assert_called_once()


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.asyncio
async def test_display_event_sets_modified_by_and_modified_at():
    mock_interaction = make_mock_interaction()
    mock_event = make_mock_event(visible=False)

    with patch("bot.crud.events_crud.get_event", return_value=mock_event), \
         patch("bot.crud.general_crud.log_change"), \
         patch("db.database.db_session") as mock_db:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminEventCommands(bot=None)
        await admin_cmds.display_event.callback(admin_cmds, mock_interaction, mock_event.event_id)

        assert mock_event.modified_by == "123"
        assert isinstance(datetime.fromisoformat(mock_event.modified_at), datetime)


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.asyncio
async def test_display_event_creates_log_entry():
    mock_interaction = make_mock_interaction()
    mock_event = make_mock_event(visible=False)

    with patch("bot.crud.events_crud.get_event", return_value=mock_event), \
         patch("bot.crud.general_crud.log_change") as mock_log, \
         patch("db.database.db_session") as mock_db:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminEventCommands(bot=None)
        await admin_cmds.display_event.callback(admin_cmds, mock_interaction, mock_event.event_id)

        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert kwargs["action"] == "edit"
        assert kwargs["performed_by"] == "123"
        assert "made visible" in kwargs["description"]


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.asyncio
async def test_hide_event_success_sets_invisible_and_sends_message():
    mock_interaction = make_mock_interaction()
    mock_event = make_mock_event(visible=True, active=False)

    with patch("bot.crud.events_crud.get_event", return_value=mock_event), \
         patch("bot.crud.general_crud.log_change") as mock_log, \
         patch("db.database.db_session") as mock_db:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminEventCommands(bot=None)
        await admin_cmds.hide_event.callback(admin_cmds, mock_interaction, mock_event.event_id)

        assert mock_event.visible is False
        mock_interaction.followup.send.assert_called_with(
            f"✅ Event `{mock_event.name} ({mock_event.event_id})` is now hidden from users."
        )
        mock_log.assert_called_once()


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.asyncio
async def test_hide_event_sets_modified_by_and_modified_at():
    mock_interaction = make_mock_interaction()
    mock_event = make_mock_event(visible=True, active=False)

    with patch("bot.crud.events_crud.get_event", return_value=mock_event), \
         patch("bot.crud.general_crud.log_change"), \
         patch("db.database.db_session") as mock_db:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminEventCommands(bot=None)
        await admin_cmds.hide_event.callback(admin_cmds, mock_interaction, mock_event.event_id)

        assert mock_event.modified_by == "123"
        assert isinstance(datetime.fromisoformat(mock_event.modified_at), datetime)


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.asyncio
async def test_hide_event_active_event_cannot_be_hidden():
    """An active event should not be allowed to be hidden."""
    mock_interaction = make_mock_interaction()
    mock_event = make_mock_event(visible=True, active=True)  # active → should block

    with patch("bot.crud.events_crud.get_event", return_value=mock_event), \
         patch("db.database.db_session") as mock_db:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminEventCommands(bot=None)
        await admin_cmds.hide_event.callback(admin_cmds, mock_interaction, mock_event.event_id)

        # It should send the "must deactivate first" error message
        mock_interaction.followup.send.assert_called_with(
            "❌ You must deactivate the event before hiding it."
        )

        # And importantly, visible should not be changed
        assert mock_event.visible is True


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.asyncio
async def test_hide_event_creates_log_entry():
    mock_interaction = make_mock_interaction()
    mock_event = make_mock_event(visible=True, active=False)

    with patch("bot.crud.events_crud.get_event", return_value=mock_event), \
         patch("bot.crud.general_crud.log_change") as mock_log, \
         patch("db.database.db_session") as mock_db:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminEventCommands(bot=None)
        await admin_cmds.hide_event.callback(admin_cmds, mock_interaction, mock_event.event_id)

        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert kwargs["action"] == "edit"
        assert kwargs["performed_by"] == "123"
        assert "marked as hidden" in kwargs["description"]


