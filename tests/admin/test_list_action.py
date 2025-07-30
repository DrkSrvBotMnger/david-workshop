import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from bot.commands.admin.actions_admin import AdminActionCommands, ACTIONS_PER_PAGE
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
async def test_list_actions_with_icons(mock_interaction):
    fake_action = make_mock_action()

    with patch("bot.commands.admin.actions_admin.get_all_actions", return_value=[fake_action]), \
         patch("db.database.db_session") as mock_db, \
         patch("bot.commands.admin.actions_admin.paginate_embeds", new_callable=AsyncMock) as mock_paginate:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminActionCommands(bot=None)
        await admin_cmds.list_actions.callback(admin_cmds, mock_interaction, show_inactive=True)

        mock_paginate.assert_called_once()
        pages = mock_paginate.call_args[0][1]
        assert any("🌐" in f.value and "📝" in f.value for f in pages[0].fields)
             

@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.action
@pytest.mark.asyncio
async def test_list_actions_pagination(mock_interaction):
    actions = [
        make_mock_action(action_key=f"action_{i}")
        for i in range(ACTIONS_PER_PAGE + 1)
    ]

    with patch("bot.commands.admin.actions_admin.get_all_actions", return_value=actions), \
         patch("db.database.db_session") as mock_db, \
         patch("bot.commands.admin.actions_admin.paginate_embeds", new_callable=AsyncMock) as mock_paginate:
        mock_db.return_value.__enter__.return_value = MagicMock()

        admin_cmds = AdminActionCommands(bot=None)
        await admin_cmds.list_actions.callback(admin_cmds, mock_interaction, show_inactive=True)

        mock_paginate.assert_called_once()
        pages = mock_paginate.call_args[0][1]
        assert len(pages) >= 2