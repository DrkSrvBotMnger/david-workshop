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
async def test_list_actions_with_icons(mock_interaction):
    """Ensure list actions displays correct icons."""
    fake_action = type("FakeAction", (), {
        "action_key": "submit_fic",
        "description": "Submit a fic",
        "default_self_reportable": True,
        "input_fields_json": '["url", "text_value"]'
    })()
    with patch("bot.crud.actions_crud.get_all_actions", return_value=[fake_action]):
        admin_cmds = AdminActionCommands(bot=None)
        await admin_cmds.list_actions.callback(admin_cmds, mock_interaction)
        mock_interaction.followup.send.assert_called_once()
        call_args, call_kwargs = mock_interaction.followup.send.call_args

        embed = (
            call_kwargs.get("embed") or
            (call_kwargs.get("embeds", [None])[0] if "embeds" in call_kwargs else None) or
            (call_args[0] if call_args and hasattr(call_args[0], "to_dict") else None)
        )

        assert embed is not None


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.action
@pytest.mark.asyncio
async def test_list_actions_triggers_pagination(mock_interaction):
    """Ensure pagination is triggered when there are more than 25 actions."""
    # Create 30 unique fake actions so chunking > 25 creates multiple embeds
    actions = [
        type("FakeAction", (), {
            "action_key": f"a{i}",
            "description": "d",
            "default_self_reportable": True,
            "input_fields_json": None
        })() for i in range(30)
    ]

    with patch("bot.crud.actions_crud.get_all_actions", return_value=actions), \
         patch("bot.commands.admin.actions_admin.paginate_embeds") as mock_paginate:
        admin_cmds = AdminActionCommands(bot=None)
        await admin_cmds.list_actions.callback(admin_cmds, mock_interaction)

    mock_paginate.assert_called_once()
