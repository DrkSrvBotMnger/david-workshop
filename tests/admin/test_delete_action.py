import pytest
from unittest.mock import AsyncMock, patch
from bot.commands.admin.actions_admin import AdminActionCommands


@pytest.fixture
def mock_interaction():
    """Mock Discord interaction for testing slash commands."""
    mock = AsyncMock()
    mock.user.id = "123"
    mock.response.defer = AsyncMock()
    mock.followup.send = AsyncMock()
    return mock
    

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