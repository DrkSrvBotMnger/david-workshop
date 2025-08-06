import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.commands.admin.rewards_admin import AdminRewardCommands
from tests.helpers import invoke_app_command


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.basic
@pytest.mark.asyncio
async def test_edit_reward_success(monkeypatch, mock_interaction):
    """Edits reward successfully when valid input."""
    cog = AdminRewardCommands(bot=None)
    fake_reward = MagicMock()
    fake_reward.reward_type = "title"

    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key", lambda *a, **k: fake_reward)
    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.reward_is_linked_to_active_event", lambda *a, **k: False)
    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.update_reward", lambda *a, **k: True)

    await invoke_app_command(
        cog.edit_reward,
        cog,
        mock_interaction,
        shortcode="t_short",
        name="New Name"
    )

    mock_interaction.followup.send.assert_awaited_with("✅ Reward `t_short` updated successfully.")


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.asyncio
async def test_edit_reward_not_found(monkeypatch, mock_interaction):
    cog = AdminRewardCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key", lambda *a, **k: None)
    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.update_reward", lambda *a, **k: pytest.fail("update_reward should not be called"))

    await invoke_app_command(
        cog.edit_reward,
        cog,
        mock_interaction,
        shortcode="missing"
    )

    mock_interaction.followup.send.assert_awaited_with("❌ Reward `missing` not found.")


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.basic
@pytest.mark.asyncio
async def test_edit_reward_linked_no_force(monkeypatch, mock_interaction):
    """Blocks edit if linked to active event without force flag."""
    cog = AdminRewardCommands(bot=None)
    fake_reward = MagicMock()
    fake_reward.reward_type = "title"

    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key", lambda *a, **k: fake_reward)
    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.reward_is_linked_to_active_event", lambda *a, **k: True)
    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.update_reward", lambda *a, **k: pytest.fail("update_reward should not be called"))

    await invoke_app_command(
        cog.edit_reward,
        cog,
        mock_interaction,
        shortcode="t_short",
        name="Should Block"
    )

    mock_interaction.followup.send.assert_awaited()
    assert any("linked to an **active event**" in str(c[0][0]) for c in mock_interaction.followup.send.await_args_list)


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.asyncio
async def test_edit_reward_linked_force_confirmed(monkeypatch, mock_interaction):
    """Allows edit if linked & force flag set with confirmation."""
    cog = AdminRewardCommands(bot=None)
    fake_reward = MagicMock()
    fake_reward.reward_type = "title"

    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key", lambda *a, **k: fake_reward)
    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.reward_is_linked_to_active_event", lambda *a, **k: True)
    monkeypatch.setattr("bot.commands.admin.rewards_admin.confirm_action", AsyncMock(return_value=True))
    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.update_reward", lambda *a, **k: True)

    await invoke_app_command(
        cog.edit_reward,
        cog,
        mock_interaction,
        shortcode="t_short",
        name="Forced Name",
        force=True
    )

    mock_interaction.followup.send.assert_awaited_with("✅ Reward `t_short` updated successfully.")


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.asyncio
async def test_edit_reward_badge_without_valid_emoji(monkeypatch, mock_interaction):
    """Fails if badge reward missing valid emoji."""
    cog = AdminRewardCommands(bot=None)
    fake_reward = MagicMock()
    fake_reward.reward_type = "badge"

    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key", lambda *a, **k: fake_reward)
    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.reward_is_linked_to_active_event", lambda *a, **k: False)
    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.update_reward", lambda *a, **k: pytest.fail("update_reward should not be called"))

    await invoke_app_command(
        cog.edit_reward,
        cog,
        mock_interaction,
        shortcode="b_short",
        emoji="invalid"
    )

    mock_interaction.followup.send.assert_awaited_with("❌ Badge rewards must have a valid emoji.")


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.basic
@pytest.mark.asyncio
async def test_edit_reward_no_valid_fields(monkeypatch, mock_interaction):
    """Fails if no valid fields are provided for update."""
    cog = AdminRewardCommands(bot=None)
    fake_reward = MagicMock()
    fake_reward.reward_type = "title"

    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key", lambda *a, **k: fake_reward)
    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.reward_is_linked_to_active_event", lambda *a, **k: False)
    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.update_reward", lambda *a, **k: pytest.fail("update_reward should not be called"))

    await invoke_app_command(
        cog.edit_reward,
        cog,
        mock_interaction,
        shortcode="t_short"
    )

    mock_interaction.followup.send.assert_awaited_with("❌ No valid fields provided to update.")
