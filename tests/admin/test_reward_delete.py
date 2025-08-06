import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.commands.admin.rewards_admin import AdminRewardCommands
from tests.helpers import invoke_app_command


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.basic
@pytest.mark.asyncio
async def test_delete_reward_success(monkeypatch, mock_interaction):
    """Deletes reward when confirmed and not linked to active event."""
    cog = AdminRewardCommands(bot=None)

    fake_reward = MagicMock()
    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key", lambda *a, **k: fake_reward)
    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.reward_is_linked_to_active_event", lambda *a, **k: False)
    monkeypatch.setattr("bot.commands.admin.rewards_admin.confirm_action", AsyncMock(return_value=True))
    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.delete_reward", lambda *a, **k: True)

    await invoke_app_command(
        cog.delete_reward,
        cog,
        mock_interaction,
        shortcode="t_short",
        reason="Cleanup old reward"
    )

    mock_interaction.edit_original_response.assert_awaited_with(content=f"✅ Reward `t_short` deleted.", view=None)


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.basic
@pytest.mark.asyncio
async def test_delete_reward_not_found(monkeypatch, mock_interaction):
    """Fails if reward is missing."""
    cog = AdminRewardCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key", lambda *a, **k: None)
    monkeypatch.setattr("bot.commands.admin.rewards_admin.confirm_action", AsyncMock(return_value=False))
    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.delete_reward", lambda *a, **k: pytest.fail("delete_reward should not be called"))

    await invoke_app_command(
        cog.delete_reward,
        cog,
        mock_interaction,
        shortcode="missing",
        reason="Does not exist"
    )

    mock_interaction.edit_original_response.assert_awaited_with(
        content="❌ Reward `missing` not found.",
        view=None
    )


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.asyncio
async def test_delete_reward_cancelled(monkeypatch, mock_interaction):
    """Cancels deletion if user declines."""
    cog = AdminRewardCommands(bot=None)

    fake_reward = MagicMock()
    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key", lambda *a, **k: fake_reward)
    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.reward_is_linked_to_active_event", lambda *a, **k: False)
    monkeypatch.setattr("bot.commands.admin.rewards_admin.confirm_action", AsyncMock(return_value=False))
    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.delete_reward", lambda *a, **k: pytest.fail("delete_reward should not be called"))

    await invoke_app_command(
        cog.delete_reward,
        cog,
        mock_interaction,
        shortcode="t_short",
        reason="User changed mind"
    )

    mock_interaction.edit_original_response.assert_awaited_with(
        content="❌ Deletion cancelled or timed out.", view=None
    )