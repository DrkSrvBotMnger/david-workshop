import pytest
from discord import Embed
from unittest.mock import AsyncMock, MagicMock
from bot.commands.admin.rewards_admin import AdminRewardCommands
from tests.helpers import invoke_app_command


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.asyncio
async def test_list_rewards_no_rewards(monkeypatch, mock_interaction):
    """Sends 'no rewards' message when there are none."""
    cog = AdminRewardCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.get_all_rewards", lambda *a, **k: [])
    monkeypatch.setattr("bot.commands.admin.rewards_admin.paginate_embeds", AsyncMock())

    await invoke_app_command(
        cog.list_rewards,
        cog,
        mock_interaction
    )

    mock_interaction.followup.send.assert_awaited_with("❌ No rewards found with those filters.")


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.asyncio
async def test_list_rewards_with_results(monkeypatch, mock_interaction):
    """Calls paginate_embeds when rewards exist."""
    cog = AdminRewardCommands(bot=None)

    fake_reward = MagicMock()
    fake_reward.reward_key = "t_test"
    fake_reward.reward_name = "Test Reward"

    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.get_all_rewards", lambda *a, **k: [fake_reward])
    paginate_mock = AsyncMock()
    monkeypatch.setattr("bot.commands.admin.rewards_admin.paginate_embeds", paginate_mock)

    await invoke_app_command(
        cog.list_rewards,
        cog,
        mock_interaction
    )

    paginate_mock.assert_awaited()


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.asyncio
async def test_show_reward_not_found(monkeypatch, mock_interaction):
    """Sends 'not found' if the reward does not exist."""
    cog = AdminRewardCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key", lambda *a, **k: None)

    await invoke_app_command(
        cog.show_reward,
        cog,
        mock_interaction,
        shortcode="t_missing"
    )

    mock_interaction.followup.send.assert_awaited_with("❌ Reward `t_missing` not found.")


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.basic
@pytest.mark.asyncio
async def test_show_reward_success(monkeypatch, mock_interaction):
    """Sends detailed embed when reward exists."""
    cog = AdminRewardCommands(bot=None)

    fake_reward = MagicMock()
    fake_reward.reward_key = "t_test"
    fake_reward.reward_name = "Test Reward"
    fake_reward.reward_type = "title"
    fake_reward.number_granted = 10
    fake_reward.reward_description = "A test reward"
    fake_reward.created_by = 1234
    fake_reward.created_at = "2025-08-05T00:00:00+00:00"
    fake_reward.modified_by = None
    fake_reward.modified_at = None

    monkeypatch.setattr(
        "bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key",
        lambda *a, **k: fake_reward
    )

    await invoke_app_command(
        cog.show_reward,
        cog,
        mock_interaction,
        shortcode="t_test"
    )

    # Just check that an Embed object was sent
    args, kwargs = mock_interaction.followup.send.await_args
    sent_embed = kwargs.get("embed") or args[0]
    assert isinstance(sent_embed, Embed)
    assert sent_embed.title.startswith("🏆 Reward Details: Test Reward")


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.basic
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reward_type,expected_fields",
    [
        ("title", {"🆔 Shortcode", "📂 Type", "📈 Number Granted", "✏️ Description", "👩‍💻 Created / Edited By"}),
        ("badge", {"🆔 Shortcode", "📂 Type", "📈 Number Granted", "✏️ Description", "🏷️ Emoji", "👩‍💻 Created / Edited By"}),
        ("preset", {"🆔 Shortcode", "📂 Type", "📈 Number Granted", "✏️ Description", "📦 Stackable",
                    "📢 Preset Channel", "🔗 Preset Message", "👩‍💻 Created / Edited By"}),
    ]
)
async def test_show_reward_embed_structure(monkeypatch, mock_interaction, reward_type, expected_fields):
    """Validates that the embed for each reward type contains the correct fields."""
    cog = AdminRewardCommands(bot=None)

    fake_reward = MagicMock()
    fake_reward.reward_key = "t_test"
    fake_reward.reward_name = "Test Reward"
    fake_reward.reward_type = reward_type
    fake_reward.number_granted = 10
    fake_reward.reward_description = "A test reward"
    fake_reward.created_by = 1234
    fake_reward.created_at = "2025-08-05T00:00:00+00:00"
    fake_reward.modified_by = None
    fake_reward.modified_at = None
    fake_reward.emoji = "😀"
    fake_reward.is_stackable = True
    fake_reward.use_channel_discord_id = "111"
    fake_reward.use_message_discord_id = "222"

    monkeypatch.setattr(
        "bot.commands.admin.rewards_admin.rewards_crud.get_reward_by_key",
        lambda *a, **k: fake_reward
    )

    await invoke_app_command(
        cog.show_reward,
        cog,
        mock_interaction,
        shortcode="t_test"
    )

    args, kwargs = mock_interaction.followup.send.await_args
    sent_embed = kwargs.get("embed") or args[0]
    assert isinstance(sent_embed, Embed)

    field_names = {f.name for f in sent_embed.fields}
    missing = expected_fields - field_names
    assert not missing, f"Missing fields for {reward_type}: {missing}"


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.asyncio
async def test_reward_logs_no_logs(monkeypatch, mock_interaction):
    """Sends 'no logs' message when there are no reward logs."""
    cog = AdminRewardCommands(bot=None)

    # Patch CRUD call to return empty list
    monkeypatch.setattr(
        "bot.commands.admin.rewards_admin.rewards_crud.get_reward_logs",
        lambda *a, **k: []
    )
    monkeypatch.setattr("bot.commands.admin.rewards_admin.paginate_embeds", AsyncMock())

    await invoke_app_command(
        cog.reward_logs,
        cog,
        mock_interaction,
        "t_test"
    )

    mock_interaction.followup.send.assert_awaited_with("❌ No logs found with those filters.")


@pytest.mark.admin
@pytest.mark.reward
@pytest.mark.basic
@pytest.mark.asyncio
async def test_reward_logs_with_results(monkeypatch, mock_interaction):
    """Calls paginate_embeds when logs are present."""
    cog = AdminRewardCommands(bot=None)

    fake_log = MagicMock()
    fake_log.log_action = "edit"
    fake_log.performed_by = "1234"
    fake_log.performed_at = "2025-08-05T00:00:00+00:00"
    fake_log.log_description = "Updated reward"

    monkeypatch.setattr(
        "bot.commands.admin.rewards_admin.rewards_crud.get_reward_logs",
        lambda *a, **k: [fake_log]
    )
    paginate_mock = AsyncMock()
    monkeypatch.setattr("bot.commands.admin.rewards_admin.paginate_embeds", paginate_mock)

    await invoke_app_command(
        cog.reward_logs,
        cog,
        mock_interaction,
        "t_test"
    )

    paginate_mock.assert_awaited()