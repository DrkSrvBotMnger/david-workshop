import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.commands.admin.rewards_admin import AdminRewardCommands
from tests.helpers import invoke_app_command


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.basic
@pytest.mark.asyncio
async def test_publishpreset_reward_not_found(monkeypatch, mock_interaction):
    """Fails if reward doesn't exist."""
    cog = AdminRewardCommands(bot=None)

    monkeypatch.setattr(
        "bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key",
        lambda *a, **k: None
    )

    await invoke_app_command(
        cog.publish_preset,
        cog,
        mock_interaction,
        shortcode="p_missing",
        message_link="https://discord.com/channels/1/2/3"
    )

    mock_interaction.followup.send.assert_awaited_with("❌ Reward `p_missing` not found.")


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.asyncio
async def test_publishpreset_not_preset_type(monkeypatch, mock_interaction):
    """Fails if reward is not type preset."""
    cog = AdminRewardCommands(bot=None)

    fake_reward = MagicMock()
    fake_reward.reward_type = "title"  # not preset

    monkeypatch.setattr(
        "bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key",
        lambda *a, **k: fake_reward
    )

    await invoke_app_command(
        cog.publish_preset,
        cog,
        mock_interaction,
        shortcode="t_test",
        message_link="https://discord.com/channels/1/2/3"
    )

    mock_interaction.followup.send.assert_awaited_with("❌ Reward `t_test` is not a publishable type of reward.")


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.asyncio
async def test_publishpreset_invalid_message_link(monkeypatch, mock_interaction):
    """Fails if message link is invalid."""
    cog = AdminRewardCommands(bot=None)

    fake_reward = MagicMock()
    fake_reward.reward_type = "preset"

    monkeypatch.setattr(
        "bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key",
        lambda *a, **k: fake_reward
    )

    with pytest.raises(ValueError) as exc_info:
        await invoke_app_command(
            cog.publish_preset,
            cog,
            mock_interaction,
            shortcode="p_test",
            message_link="invalid-link"
        )

    assert "Invalid Discord message link format." in str(exc_info.value)


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.basic
@pytest.mark.asyncio
async def test_publishpreset_success(monkeypatch, mock_interaction):
    """Publishes preset successfully (skips old preset archive/delete)."""
    cog = AdminRewardCommands(bot=None)

    fake_reward = MagicMock()
    fake_reward.reward_type = "preset"
    fake_reward.use_channel_discord_id = None
    fake_reward.use_message_discord_id = None

    monkeypatch.setattr(
        "bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key",
        lambda *a, **k: fake_reward
    )
    monkeypatch.setattr(
        "bot.commands.admin.rewards_admin.rewards_crud.reward_is_linked_to_active_event",
        lambda *a, **k: False
    )
    monkeypatch.setattr(
        "bot.commands.admin.rewards_admin.rewards_crud.publish_preset",
        lambda *a, **k: True
    )

    # Fake message with async delete
    fake_message = MagicMock()
    fake_message.delete = AsyncMock()

    # Fake channel that returns the fake message
    fake_channel = MagicMock()
    fake_channel.fetch_message = AsyncMock(return_value=fake_message)

    # Patch self.bot.fetch_channel in the Cog
    cog.bot = MagicMock()
    cog.bot.fetch_channel = AsyncMock(return_value=fake_channel)

    # Also patch preset channel lookup to avoid "channel not found"
    preset_channel = MagicMock()
    preset_channel.send = AsyncMock(side_effect=[MagicMock(id=111), MagicMock(id=222)])
    mock_interaction.guild.get_channel = lambda x: preset_channel

    await invoke_app_command(
        cog.publish_preset,
        cog,
        mock_interaction,
        shortcode="p_test",
        message_link="https://discord.com/channels/1/2/3"
    )

    mock_interaction.followup.send.assert_awaited()
    sent_message = str(mock_interaction.followup.send.await_args[0][0])
    assert "✅ Preset published" in sent_message
