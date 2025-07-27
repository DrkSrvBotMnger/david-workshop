import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bot.commands.admin import AdminCommands
from bot.utils import is_admin_or_mod

@pytest.fixture
def mock_interaction():
    mock = MagicMock()
    mock.user.id = 1234
    mock.user.mention = "<@1234>"
    mock.response.defer = AsyncMock()
    mock.followup.send = AsyncMock()
    mock.guild.get_channel = MagicMock(return_value=AsyncMock(send=AsyncMock()))
    return mock


# Testing admin rights
@pytest.mark.asyncio
async def test_is_admin_or_mod_false_for_regular_user():
    mock_member = MagicMock()
    mock_member.guild_permissions.administrator = False
    mock_member.roles = []  # No roles

    mock_guild = MagicMock()
    mock_guild.fetch_member = AsyncMock(return_value=mock_member)

    mock_interaction = MagicMock()
    mock_interaction.user.id = 9999
    mock_interaction.guild = mock_guild

    result = await is_admin_or_mod(mock_interaction)
    assert result is False


@pytest.mark.asyncio
async def test_is_admin_or_mod_true_if_admin():
    mock_member = MagicMock()
    mock_member.guild_permissions.administrator = True
    mock_member.roles = []

    mock_guild = MagicMock()
    mock_guild.fetch_member = AsyncMock(return_value=mock_member)

    mock_interaction = MagicMock()
    mock_interaction.user.id = 1234
    mock_interaction.guild = mock_guild

    result = await is_admin_or_mod(mock_interaction)
    assert result is True


@pytest.mark.asyncio
async def test_is_admin_or_mod_true_if_mod_role_matches():
    from bot import utils
    mock_member = MagicMock()
    mock_member.guild_permissions.administrator = False

    mock_mod_role = MagicMock()
    mock_mod_role.id = utils.MOD_ROLE_IDS[0] if utils.MOD_ROLE_IDS else 123456789
    mock_member.roles = [mock_mod_role]

    mock_guild = MagicMock()
    mock_guild.fetch_member = AsyncMock(return_value=mock_member)

    mock_interaction = MagicMock()
    mock_interaction.user.id = 1234
    mock_interaction.guild = mock_guild

    with patch("bot.utils.MOD_ROLE_IDS", [mock_mod_role.id]):
        result = await is_admin_or_mod(mock_interaction)
        assert result is True

# Create event tests
@pytest.mark.asyncio
async def test_create_event_invalid_start_date(mock_interaction):
    admin_cmds = AdminCommands(bot=None)

    await admin_cmds.create_event.callback(
        admin_cmds,
        interaction=mock_interaction,
        shortcode="testevent",
        name="Test Event",
        description="desc",
        start_date="invalid-date",
        end_date=None,
        coordinator=None,
        tags=None,
        embed_channel=None,
        embed_message_id=None,
        role_id=None,
        priority=0,
        shop_section_id=None
    )

    mock_interaction.followup.send.assert_called_once_with(
        "❌ Invalid start date format. Use YYYY-MM-DD."
    )


@pytest.mark.asyncio
async def test_create_event_invalid_end_date(mock_interaction):
    admin_cmds = AdminCommands(bot=None)

    await admin_cmds.create_event.callback(
        admin_cmds,
        interaction=mock_interaction,
        shortcode="testevent",
        name="Test Event",
        description="desc",
        start_date="2025-08-01",
        end_date="not-a-date",
        coordinator=None,
        tags=None,
        embed_channel=None,
        embed_message_id=None,
        role_id=None,
        priority=0,
        shop_section_id=None
    )

    mock_interaction.followup.send.assert_called_once_with(
        "❌ Invalid end date format. Use YYYY-MM-DD or leave empty."
    )


@pytest.mark.asyncio
async def test_create_event_default_coordinator(mock_interaction):
    admin_cmds = AdminCommands(bot=None)

    with patch("bot.crud.get_event", return_value=None), \
     patch("bot.crud.create_event") as mock_create, \
     patch("bot.commands.admin.EMBED_CHANNEL_ID", new="999999999"):

        await admin_cmds.create_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            shortcode="testevent",
            name="Test Event",
            description="desc",
            start_date="2025-08-01",
            end_date=None,
            coordinator=None,
            tags=None,
            embed_channel=None,
            embed_message_id=None,
            role_id=None,
            priority=0,
            shop_section_id=None
        )
    
    assert mock_create.called
    args, kwargs = mock_create.call_args
    assert kwargs["coordinator_id"] == str(mock_interaction.user.id)
    assert kwargs["embed_channel_id"] == "999999999"
    assert kwargs["event_id"] == "testevent_2025_08"


@pytest.mark.asyncio
async def test_create_event_duplicate_event_id(mock_interaction):
    admin_cmds = AdminCommands(bot=None)

    mock_event = MagicMock()
    with patch("bot.crud.get_event", return_value=mock_event):
        await admin_cmds.create_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            shortcode="testevent",
            name="Test Event",
            description="desc",
            start_date="2025-08-01",
            end_date=None,
            coordinator=None,
            tags=None,
            embed_channel=None,
            embed_message_id=None,
            role_id=None,
            priority=0,
            shop_section_id=None
        )

        mock_interaction.followup.send.assert_called_once_with(
            "❌ An event with ID `testevent_2025_08` already exists. Choose a different shortcode or start date."
        )


@pytest.mark.asyncio
async def test_create_event_success_message(mock_interaction):
    admin_cmds = AdminCommands(bot=None)

    mock_created_event = MagicMock()
    mock_created_event.name = "Test Event"

    with patch("bot.crud.get_event", return_value=None), \
         patch("bot.crud.create_event", return_value=mock_created_event):

        await admin_cmds.create_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            shortcode="testevent",
            name="Test Event",
            description="desc",
            start_date="2025-08-01",
            end_date=None,
            coordinator=None,
            tags=None,
            embed_channel=None,
            embed_message_id=None,
            role_id=None,
            priority=0,
            shop_section_id=None
        )
            
        mock_interaction.followup.send.assert_called_once_with(
            content="✅ Event `Test Event` created with ID `testevent_2025_08`.\n👤 Coordinator: <@1234> *(defaulted to you)*"
        )


# Edit event tests
@pytest.mark.asyncio
async def test_edit_event_blocks_active(mock_interaction):
    admin_cmds = AdminCommands(bot=None)

    mock_event = MagicMock()
    mock_event.active = True
    with patch("bot.crud.get_event", return_value=mock_event):
        await admin_cmds.edit_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            event_id="testevent",
            name="Edited",
            description=None,
            start_date=None,
            end_date=None,
            coordinator=None,
            tags=None,
            embed_channel=None,
            embed_message_id=None,
            role_id=None,
            priority=None,
            shop_section_id=None,
            reason=None
        )
        mock_interaction.followup.send.assert_called_once_with(
            "⚠️ This event is active and cannot be edited. Use a separate command to deactivate it first."
        )


@pytest.mark.asyncio
async def test_clear_keyword_removes_tags(mock_interaction):
    admin_cmds = AdminCommands(bot=None)

    mock_event = MagicMock()
    mock_event.active = False
    mock_event.visible = False
    with patch("bot.crud.get_event", return_value=mock_event), \
         patch("bot.crud.update_event", return_value=True):
        await admin_cmds.edit_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            event_id="testevent",
            name=None,
            description=None,
            start_date=None,
            end_date=None,
            coordinator=None,
            tags="CLEAR",
            embed_channel=None,
            embed_message_id=None,
            role_id=None,
            priority=None,
            shop_section_id=None,
            reason=None
        )

        mock_interaction.followup.send.assert_called()