import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from bot.commands.admin.actions_admin import AdminActionCommands, ACTIONS_PER_PAGE


# --- Helpers ---
def make_mock_action(**kwargs):
    """Builds a mock Action object for admin_action tests."""
    action = MagicMock()
    action.action_key = kwargs.get("action_key", "submit_fic")
    action.description = kwargs.get("description", "Submit a fic")
    action.input_fields_json = kwargs.get("input_fields_json", '["url", "text_value"]')
    action.active = kwargs.get("active", True)
    action.created_at = kwargs.get("created_at", datetime.utcnow())
    action.modified_at = kwargs.get("modified_at", datetime.utcnow())
    action.deactivated_at = kwargs.get("deactivated_at", None)
    return action


@pytest.fixture
def mock_interaction():
    """Mock Discord interaction for testing slash commands."""
    inter = AsyncMock()
    inter.user.id = "123"
    inter.followup.send = AsyncMock()
    inter.response.defer = AsyncMock()
    mock_channel = MagicMock()
    mock_channel.send = AsyncMock()
    inter.guild = MagicMock()
    inter.guild.get_channel = MagicMock(return_value=mock_channel)
    return inter


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.action
@pytest.mark.asyncio
async def test_deactivate_action_success(mock_interaction):
    """Successfully deactivates an active action."""
    mock_action = make_mock_action(action_key="submit_fic", active=True)

    def fake_get_action_by_key(session, key):
        # Original action exists, versioned key does not
        if key == "submit_fic":
            return mock_action
        return None

    with patch("bot.commands.admin.actions_admin.get_action_by_key", side_effect=fake_get_action_by_key), \
         patch("db.database.db_session") as mock_db:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminActionCommands(bot=None)
        await admin_cmds.deactivate_action.callback(admin_cmds, mock_interaction, "submit_fic")

        mock_interaction.followup.send.assert_called_once()
        sent_msg = mock_interaction.followup.send.call_args[0][0]
        assert "deactivated" in sent_msg.lower()
        assert "_v1" in mock_action.action_key


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.action
@pytest.mark.asyncio
async def test_deactivate_action_already_inactive(mock_interaction):
    """Rejects deactivation if already inactive."""
    mock_action = make_mock_action(active=False)
    with patch("bot.commands.admin.actions_admin.get_action_by_key", return_value=mock_action), \
         patch("db.database.db_session") as mock_db:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminActionCommands(bot=None)
        await admin_cmds.deactivate_action.callback(admin_cmds, mock_interaction, "submit_fic")

        mock_interaction.followup.send.assert_called_once()
        assert "already inactive" in mock_interaction.followup.send.call_args[0][0].lower()


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.action
@pytest.mark.asyncio
async def test_deactivate_action_not_found(mock_interaction):
    """Rejects deactivation if action not found."""
    with patch("bot.commands.admin.actions_admin.get_action_by_key", return_value=None), \
         patch("db.database.db_session") as mock_db:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminActionCommands(bot=None)
        await admin_cmds.deactivate_action.callback(admin_cmds, mock_interaction, "unknown_action")

        mock_interaction.followup.send.assert_called_once()
        assert "does not exist" in mock_interaction.followup.send.call_args[0][0].lower()
