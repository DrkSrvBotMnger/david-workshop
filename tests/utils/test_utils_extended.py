import pytest
import discord
from unittest.mock import AsyncMock, MagicMock, patch

from bot import utils


# --- now_iso / now_unix ---
@pytest.mark.utils
@pytest.mark.basic
def test_now_iso_and_now_unix_return_expected_formats():
    """ Ensure now_iso returns ISO 8601 format and now_unix returns Unix timestamp. """
    
    iso_value = utils.now_iso()
    unix_value = utils.now_unix()

    assert isinstance(iso_value, str)
    assert "T" in iso_value and "+" in iso_value  # ISO 8601 format
    assert isinstance(unix_value, int)
    assert unix_value > 0


# --- parse_message_link ---
@pytest.mark.utils
def test_parse_message_link_valid():
    """ Ensure parse_message_link correctly extracts channel and message IDs. """
    
    channel_id, message_id = utils.parse_message_link(
        "https://discord.com/channels/123456789012345678/987654321098765432/112233445566778899"
    )
    assert channel_id == 987654321098765432
    assert message_id == 112233445566778899


@pytest.mark.utils
def test_parse_message_link_invalid():
    """ Ensure parse_message_link raises ValueError for invalid links."""
    
    with pytest.raises(ValueError):
        utils.parse_message_link("invalid-link")


# --- admin_or_mod_check ---
@pytest.mark.utils
def test_admin_or_mod_check_returns_check_object():
    """ Ensure admin_or_mod_check returns a callable check object. """
    
    check_obj = utils.admin_or_mod_check()
    assert hasattr(check_obj, "__call__")  # discord.app_commands.check returns a callable wrapper


# --- ConfirmActionView ---
@pytest.mark.utils
@pytest.mark.basic
@pytest.mark.asyncio
async def test_confirm_action_view_confirm_and_cancel():
    view = utils.ConfirmActionView()

    # Simulate confirm button click
    interaction = MagicMock()
    interaction.response.defer = AsyncMock()
    await utils.ConfirmActionView.confirm(view, interaction, MagicMock())
    assert view.confirmed is True

    # Simulate cancel button click
    view.confirmed = None
    await utils.ConfirmActionView.cancel(view, interaction, MagicMock())
    assert view.confirmed is False


@pytest.mark.utils
@pytest.mark.asyncio
async def test_confirm_action_view_timeout_disables_buttons():
    """ Ensure timeout disables all buttons and edits the message. """
    
    view = utils.ConfirmActionView()
    fake_button = discord.ui.Button(label="Test")
    view.add_item(fake_button)

    message_mock = AsyncMock()
    view.message = message_mock

    await view.on_timeout()

    # All buttons should be disabled
    for child in view.children:
        assert getattr(child, "disabled", False) is True
    message_mock.edit.assert_awaited()


# --- confirm_action ---
@pytest.mark.utils
@pytest.mark.basic
@pytest.mark.asyncio
async def test_confirm_action_returns_true():
    """ Ensure confirm_action returns True if confirmed. """
    
    with patch.object(utils, "ConfirmActionView") as mock_view_cls:
        mock_view = AsyncMock()
        mock_view.wait = AsyncMock()
        mock_view.confirmed = True
        mock_view_cls.return_value = mock_view

        interaction = AsyncMock()
        result = await utils.confirm_action(interaction, "Test Item", "Reason")
        assert result is True


@pytest.mark.utils
@pytest.mark.basic
@pytest.mark.asyncio
async def test_confirm_action_returns_false_if_not_confirmed():
    """ Ensure confirm_action returns False if not confirmed. """
    
    with patch.object(utils, "ConfirmActionView") as mock_view_cls:
        mock_view = AsyncMock()
        mock_view.wait = AsyncMock()
        mock_view.confirmed = False
        mock_view_cls.return_value = mock_view

        interaction = AsyncMock()
        result = await utils.confirm_action(interaction, "Test Item", "Reason")
        assert result is False


# --- EmbedPaginator ---
@pytest.mark.utils
@pytest.mark.basic
@pytest.mark.asyncio
async def test_embed_paginator_navigation_changes_pages():
    """ Ensure navigation buttons change the current page. """
    
    embeds = [discord.Embed(title=f"Page {i+1}") for i in range(3)]
    paginator = utils.EmbedPaginator(embeds)

    # Mock interaction
    interaction = MagicMock()
    interaction.response.edit_message = AsyncMock()

    # Navigate forward and backward
    await paginator.next_page(interaction)
    assert paginator.current_page == 1

    await paginator.go_last(interaction)
    assert paginator.current_page == 2

    await paginator.prev_page(interaction)
    assert paginator.current_page == 1

    await paginator.go_first(interaction)
    assert paginator.current_page == 0


# --- paginate_embeds ---
@pytest.mark.utils
@pytest.mark.asyncio
async def test_paginate_embeds_no_embeds_sends_error():
    """ Ensure paginate_embeds sends an error message if no embeds are provided. """
    
    interaction = AsyncMock()
    interaction.followup.send = AsyncMock()

    await utils.paginate_embeds(interaction, [])
    interaction.followup.send.assert_awaited_with(
        "❌ No data to display.", ephemeral=True
    )


@pytest.mark.utils
@pytest.mark.asyncio
async def test_paginate_embeds_single_embed_disables_buttons():
    """ Ensure paginate_embeds disables all buttons if only one embed is provided. """
    embed = discord.Embed(title="Only page")
    interaction = AsyncMock()
    interaction.followup.send = AsyncMock()

    await utils.paginate_embeds(interaction, [embed])
    # Ensure followup.send called with view containing all disabled buttons
    sent_view = interaction.followup.send.call_args[1]["view"]
    assert all(btn.disabled for btn in sent_view.children)


@pytest.mark.utils
@pytest.mark.asyncio
async def test_paginate_embeds_multiple_embeds_first_page_buttons_disabled():
    """ Ensure paginate_embeds disables first and prev buttons on the first page. """
    
    embeds = [discord.Embed(title=f"Page {i+1}") for i in range(2)]
    interaction = AsyncMock()
    interaction.followup.send = AsyncMock()

    await utils.paginate_embeds(interaction, embeds)
    sent_view = interaction.followup.send.call_args[1]["view"]
    assert sent_view.first_button.disabled
    assert sent_view.prev_button.disabled


# --- post_announcement_message ---
@pytest.mark.utils
@pytest.mark.basic
@pytest.mark.asyncio
async def test_post_announcement_message_sends_message_with_and_without_role():
    """ Ensure post_announcement_message sends the message with and without a role mention. """
    
    mock_channel = AsyncMock()
    mock_channel.send = AsyncMock(return_value="sent")
    mock_guild = MagicMock()
    mock_guild.get_channel = MagicMock(return_value=mock_channel)

    interaction = MagicMock()
    interaction.guild = mock_guild

    # Without role mention
    result = await utils.post_announcement_message(interaction, "12345", "Hello")
    assert result == "sent"

    # With role mention
    result = await utils.post_announcement_message(interaction, "12345", "Hello", "98765")
    assert "<@&98765>" in mock_channel.send.call_args[0][0]


@pytest.mark.utils
@pytest.mark.asyncio
async def test_post_announcement_message_invalid_channel_returns_none():
    """ Ensure post_announcement_message returns None if the channel is invalid. """
    
    mock_guild = MagicMock()
    mock_guild.get_channel = MagicMock(return_value=None)

    interaction = MagicMock()
    interaction.guild = mock_guild

    result = await utils.post_announcement_message(interaction, "12345", "Hello")
    assert result is None


@pytest.mark.utils
@pytest.mark.asyncio
async def test_post_announcement_message_exception_returns_none():
    """ Ensure post_announcement_message returns None if an exception occurs. """
    
    mock_guild = MagicMock()
    mock_guild.get_channel = MagicMock(side_effect=Exception("Test error"))

    interaction = MagicMock()
    interaction.guild = mock_guild

    result = await utils.post_announcement_message(interaction, "12345", "Hello")
    assert result is None
