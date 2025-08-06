import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.commands.admin.rewards_admin import AdminRewardCommands
from tests.helpers import invoke_app_command


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.basic
@pytest.mark.asyncio
async def test_create_reward_success(monkeypatch, mock_interaction):
    """Should create reward successfully when valid input."""
    cog = AdminRewardCommands(bot=None)

    # Patch CRUD lookups
    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key", lambda *a, **k: None)
    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.create_reward", lambda *a, **k: True)

    await invoke_app_command(
        cog.create_reward,
        cog,
        mock_interaction,
        shortcode="short",
        reward_type="title",
        name="My Reward"
    )

    mock_interaction.followup.send.assert_awaited_with("✅ Reward `My Reward` created with shortcode `t_short`.")


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.asyncio
async def test_create_reward_fails_if_badge_without_emoji(monkeypatch, mock_interaction):
    cog = AdminRewardCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key", lambda *a, **k: None)

    await invoke_app_command(
        cog.create_reward,
        cog,
        mock_interaction,
        shortcode="short",
        reward_type="badge",
        name="Badge Reward"
    )

    mock_interaction.followup.send.assert_awaited_with("❌ Badge rewards must have an emoji.")


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.basic
@pytest.mark.asyncio
async def test_create_reward_fails_if_already_exists(monkeypatch, mock_interaction):
    cog = AdminRewardCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key", lambda *a, **k: True)

    await invoke_app_command(
        cog.create_reward,
        cog,
        mock_interaction,
        shortcode="short",
        reward_type="title",
        name="Duplicate Reward"
    )

    mock_interaction.followup.send.assert_awaited_with("❌ Reward `t_short` already exists.")


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.asyncio
async def test_create_reward_removes_emoji_for_non_badge(monkeypatch, mock_interaction):
    """Emoji should be removed automatically for non-badge rewards."""
    cog = AdminRewardCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key", lambda *a, **k: None)
    called_data = {}

    def fake_create_reward(session=None, reward_create_data=None):
        called_data.update(reward_create_data)
        return True

    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.create_reward", fake_create_reward)

    await invoke_app_command(
        cog.create_reward,
        cog,
        mock_interaction,
        shortcode="short",
        reward_type="title",
        name="No Emoji",
        emoji="😀"
    )

    assert called_data.get("emoji") is None
    mock_interaction.followup.send.assert_awaited()


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.asyncio
async def test_create_reward_forces_non_stackable_on_invalid_type(monkeypatch, mock_interaction):
    """Should force is_stackable=False for reward types that can't stack."""
    cog = AdminRewardCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key", lambda *a, **k: None)
    captured_data = {}

    def fake_create_reward(session=None, reward_create_data=None):
        captured_data.update(reward_create_data)
        return True

    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.create_reward", fake_create_reward)

    await invoke_app_command(
        cog.create_reward,
        cog,
        mock_interaction,
        shortcode="short",
        reward_type="title",  # Non-stackable type
        name="Stackable Test",
        stackable=True
    )

    assert captured_data.get("is_stackable") is False
    mock_interaction.followup.send.assert_awaited()