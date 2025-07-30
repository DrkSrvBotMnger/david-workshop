import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from bot.commands.admin.actions_admin import AdminActionCommands
from datetime import datetime


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
async def test_delete_action_success(mock_interaction):
    """Ensure actions are deleted successfully."""
    with patch("bot.crud.actions_crud.get_action_by_key", return_value=True), \
         patch("bot.crud.actions_crud.delete_action", return_value=True):

        admin_cmds = AdminActionCommands(bot=None)

        await admin_cmds.delete_action.callback(
            admin_cmds,
            mock_interaction,
            action_key="submit_fic"
        )

        mock_interaction.followup.send.assert_called_once()
        assert "deleted successfully" in mock_interaction.followup.send.call_args[0][0]


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.action
@pytest.mark.asyncio
async def test_delete_action_rejects_nonexistent(mock_interaction):
    """Ensure delete action fails gracefully if action doesn't exist."""
    with patch("bot.crud.actions_crud.get_action_by_key", return_value=None):
        admin_cmds = AdminActionCommands(bot=None)
        await admin_cmds.delete_action.callback(
            admin_cmds,
            mock_interaction,
            action_key="does_not_exist"
        )
        mock_interaction.followup.send.assert_called_once()
        sent_msg = mock_interaction.followup.send.call_args[0][0]
        assert "does not exist" in sent_msg


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.action
@pytest.mark.asyncio
async def test_delete_action_inactive(mock_interaction):
    """Rejects deletion if action is inactive."""
    mock_action = make_mock_action(active=False)
    with patch("bot.commands.admin.actions_admin.get_action_by_key", return_value=mock_action), \
         patch("bot.commands.admin.actions_admin.action_is_used", return_value=False), \
         patch("db.database.db_session") as mock_db:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminActionCommands(bot=None)
        await admin_cmds.delete_action.callback(admin_cmds, mock_interaction, "submit_fic")

        mock_interaction.followup.send.assert_called_once()
        assert "inactive" in mock_interaction.followup.send.call_args[0][0].lower()


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.action
@pytest.mark.asyncio
async def test_delete_action_in_use(mock_interaction):
    """Rejects deletion if action is referenced in user history."""
    mock_action = make_mock_action(active=True)
    with patch("bot.commands.admin.actions_admin.get_action_by_key", return_value=mock_action), \
         patch("bot.commands.admin.actions_admin.action_is_used", return_value=True), \
         patch("db.database.db_session") as mock_db:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminActionCommands(bot=None)
        await admin_cmds.delete_action.callback(admin_cmds, mock_interaction, "submit_fic")

        mock_interaction.followup.send.assert_called_once()
        assert "user history" in mock_interaction.followup.send.call_args[0][0].lower()