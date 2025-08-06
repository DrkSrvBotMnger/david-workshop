import pytest
from unittest.mock import MagicMock, AsyncMock
from bot.commands.admin.actions_admin import AdminActionCommands
from tests.helpers import invoke_app_command


# === CREATE ===
@pytest.mark.admin
@pytest.mark.action
@pytest.mark.basic
@pytest.mark.asyncio
async def test_create_action_success(monkeypatch, mock_interaction):
    """Creates a new action successfully."""
    cog = AdminActionCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.actions_admin.actions_crud.get_action_by_key", lambda *a, **k: None)
    monkeypatch.setattr("bot.commands.admin.actions_admin.actions_crud.create_action", lambda *a, **k: True)

    await invoke_app_command(
        cog.create_action,
        cog,
        mock_interaction,
        "myaction",
        "Test action"
    )

    mock_interaction.followup.send.assert_awaited()
    sent = mock_interaction.followup.send.await_args[0][0]
    assert "✅ **Action Created**" in sent


@pytest.mark.admin
@pytest.mark.action
@pytest.mark.asyncio
async def test_create_action_invalid_key(monkeypatch, mock_interaction):
    """Fails if key is invalid."""
    cog = AdminActionCommands(bot=None)

    await invoke_app_command(
        cog.create_action,
        cog,
        mock_interaction,
        "BAD KEY",  # spaces invalid
        "Test action"
    )

    mock_interaction.followup.send.assert_awaited()
    sent = mock_interaction.followup.send.await_args[0][0]
    assert "❌ Action key must be lowercase letters, numbers, and underscores only (e.g. `submit_fic`)." in sent


@pytest.mark.admin
@pytest.mark.action
@pytest.mark.asyncio
async def test_create_action_already_exists(monkeypatch, mock_interaction):
    """Fails if action already exists."""
    cog = AdminActionCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.actions_admin.actions_crud.get_action_by_key", lambda *a, **k: MagicMock())

    await invoke_app_command(
        cog.create_action,
        cog,
        mock_interaction,
        "exists",
        "Test action"
    )

    mock_interaction.followup.send.assert_awaited_with("❌ Action `exists` already exists.")


# === DELETE ===
@pytest.mark.admin
@pytest.mark.action
@pytest.mark.basic
@pytest.mark.asyncio
async def test_delete_action_success(monkeypatch, mock_interaction):
    """Deletes action successfully."""
    cog = AdminActionCommands(bot=None)

    fake_action = MagicMock()
    fake_action.is_active = True
    monkeypatch.setattr("bot.commands.admin.actions_admin.actions_crud.get_action_by_key", lambda *a, **k: fake_action)
    monkeypatch.setattr("bot.commands.admin.actions_admin.action_is_used", lambda *a, **k: False)
    monkeypatch.setattr("bot.commands.admin.actions_admin.actions_crud.delete_action", lambda *a, **k: True)

    await invoke_app_command(
        cog.delete_action,
        cog,
        mock_interaction,
        "delme"
    )

    mock_interaction.followup.send.assert_awaited()
    sent = mock_interaction.followup.send.await_args[0][0]
    assert "🗑️ Action `delme` deleted successfully." in sent


@pytest.mark.admin
@pytest.mark.action
@pytest.mark.asyncio
async def test_delete_action_not_found(monkeypatch, mock_interaction):
    """Fails if action not found."""
    cog = AdminActionCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.actions_admin.actions_crud.get_action_by_key", lambda *a, **k: None)

    await invoke_app_command(
        cog.delete_action,
        cog,
        mock_interaction,
        "missing"
    )

    mock_interaction.followup.send.assert_awaited_with("❌ Action `missing` does not exist.")


@pytest.mark.admin
@pytest.mark.action
@pytest.mark.asyncio
async def test_delete_action_in_use(monkeypatch, mock_interaction):
    """Fails if action is in use."""
    cog = AdminActionCommands(bot=None)

    fake_action = MagicMock()
    fake_action.is_active = True
    monkeypatch.setattr("bot.commands.admin.actions_admin.actions_crud.get_action_by_key", lambda *a, **k: fake_action)
    monkeypatch.setattr("bot.commands.admin.actions_admin.action_is_used", lambda *a, **k: True)

    await invoke_app_command(
        cog.delete_action,
        cog,
        mock_interaction,
        "busy"
    )

    mock_interaction.followup.send.assert_awaited()
    sent = mock_interaction.followup.send.await_args[0][0]
    assert "❌ Action `busy` is referenced in user history and cannot be deleted." in sent


# === DEACTIVATE ===
@pytest.mark.admin
@pytest.mark.action
@pytest.mark.basic
@pytest.mark.asyncio
async def test_deactivate_action_success(monkeypatch, mock_interaction):
    """Deactivates action successfully."""
    cog = AdminActionCommands(bot=None)

    fake_action = MagicMock()
    fake_action.is_active = True

    # Return the fake_action for the original lookup, then None for the new version key
    def fake_get_action_by_key(session, key):
        # The loop will stop when None is returned for the versioned key
        if key.endswith("_v1"):
            return None
        return fake_action

    monkeypatch.setattr(
        "bot.commands.admin.actions_admin.actions_crud.get_action_by_key",
        fake_get_action_by_key
    )

    # Patch deactivate_action to pretend the DB update worked
    monkeypatch.setattr(
        "bot.commands.admin.actions_admin.actions_crud.deactivate_action",
        lambda *a, **k: True
    )

    await invoke_app_command(
        cog.deactivate_action,
        cog,
        mock_interaction,
        "myaction"
    )

    mock_interaction.followup.send.assert_awaited()
    sent = mock_interaction.followup.send.await_args[0][0]
    assert "✅ Action `myaction` has been deactivated and renamed to `myaction_v1`" in sent


@pytest.mark.admin
@pytest.mark.action
@pytest.mark.asyncio
async def test_deactivate_action_not_found(monkeypatch, mock_interaction):
    """Fails if action not found."""
    cog = AdminActionCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.actions_admin.actions_crud.get_action_by_key", lambda *a, **k: None)

    await invoke_app_command(
        cog.deactivate_action,
        cog,
        mock_interaction,
        "missing"
    )

    mock_interaction.followup.send.assert_awaited_with("❌ Action `missing` does not exist.")


@pytest.mark.admin
@pytest.mark.action
@pytest.mark.asyncio
async def test_deactivate_action_already_inactive(monkeypatch, mock_interaction):
    """Fails if already inactive."""
    cog = AdminActionCommands(bot=None)

    # Realistic fake action
    fake_action = MagicMock()
    fake_action.is_active = False
    fake_action.action_key = "inactive"

    # Ensure we return this fake action
    monkeypatch.setattr(
        "bot.commands.admin.actions_admin.actions_crud.get_action_by_key",
        lambda *a, **k: fake_action
    )

    # Force AsyncMock to avoid hanging
    mock_interaction.followup.send = AsyncMock()

    await invoke_app_command(
        cog.deactivate_action,
        cog,
        mock_interaction,
        "inactive"
    )

    mock_interaction.followup.send.assert_awaited()
    sent = mock_interaction.followup.send.await_args[0][0]
    assert "⚠️ Action `inactive` is already inactive." in sent


# === LIST ===
@pytest.mark.admin
@pytest.mark.action
@pytest.mark.asyncio
async def test_list_actions_none(monkeypatch, mock_interaction):
    """No actions found."""
    cog = AdminActionCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.actions_admin.actions_crud.get_all_actions", lambda *a, **k: [])
    monkeypatch.setattr("bot.commands.admin.actions_admin.paginate_embeds", AsyncMock())

    await invoke_app_command(
        cog.list_actions,
        cog,
        mock_interaction
    )

    mock_interaction.followup.send.assert_awaited_with("ℹ️ No actions found with the current filters.")


@pytest.mark.admin
@pytest.mark.action
@pytest.mark.basic
@pytest.mark.asyncio
async def test_list_actions_with_results(monkeypatch, mock_interaction):
    """Lists actions successfully."""
    cog = AdminActionCommands(bot=None)

    fake_action = MagicMock()
    monkeypatch.setattr("bot.commands.admin.actions_admin.actions_crud.get_all_actions", lambda *a, **k: [fake_action])
    pag_mock = AsyncMock()
    monkeypatch.setattr("bot.commands.admin.actions_admin.paginate_embeds", pag_mock)

    await invoke_app_command(
        cog.list_actions,
        cog,
        mock_interaction
    )

    pag_mock.assert_awaited()