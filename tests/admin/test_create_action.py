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
async def test_create_action_success(mock_interaction):
    """Ensure a valid action is created successfully."""
    with patch("bot.crud.actions_crud.get_action_by_key", return_value=None), \
         patch("bot.crud.actions_crud.create_action", return_value=None):

        admin_cmds = AdminActionCommands(bot=None)

        await admin_cmds.create_action.callback(
            admin_cmds,
            mock_interaction,
            action_key="submit_fic",
            description="Submit a fanfiction",
            default_self_reportable=True,
            input_fields="url,text_value"
        )

        mock_interaction.followup.send.assert_called_once()

        # Extract sent message
        sent_message = mock_interaction.followup.send.call_args
        
        # Positional content
        positional_content = sent_message[0][0] if sent_message[0] else ""
        
        # Keyword content
        keyword_content = sent_message[1].get("content", "")
        
        # Embeds (just in case)
        embed = sent_message[1].get("embed", None)
        embed_desc = getattr(embed, "description", "") if embed else ""
        embed_title = getattr(embed, "title", "") if embed else ""
        
        embeds_list = sent_message[1].get("embeds", [])
        embeds_text = " ".join(
            (getattr(e, "description", "") or "") + " " + (getattr(e, "title", "") or "")
            for e in embeds_list
        ) if embeds_list else ""
        
        assert (
            "submit_fic" in positional_content
            or "submit_fic" in keyword_content
            or "submit_fic" in embed_desc
            or "submit_fic" in embed_title
            or "submit_fic" in embeds_text
        )


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.action
@pytest.mark.asyncio
async def test_create_action_duplicate(mock_interaction):
    """Ensure duplicate keys are rejected."""
    with patch("bot.crud.actions_crud.get_action_by_key", return_value=True):
        admin_cmds = AdminActionCommands(bot=None)

        await admin_cmds.create_action.callback(
            admin_cmds,
            mock_interaction,
            action_key="submit_fic",
            description="Submit a fanfiction"
        )

        mock_interaction.followup.send.assert_called_once()
        assert "already exists" in mock_interaction.followup.send.call_args[0][0]


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.action
@pytest.mark.asyncio
async def test_create_action_invalid_input_field(mock_interaction):
    """Ensure invalid input fields are rejected."""
    with patch("bot.crud.actions_crud.get_action_by_key", return_value=None):
        admin_cmds = AdminActionCommands(bot=None)

        await admin_cmds.create_action.callback(
            admin_cmds,
            mock_interaction,
            action_key="submit_art",
            description="Submit art",
            input_fields="not_a_field"
        )

        mock_interaction.followup.send.assert_called_once()
        assert "Invalid input field" in mock_interaction.followup.send.call_args[0][0]

