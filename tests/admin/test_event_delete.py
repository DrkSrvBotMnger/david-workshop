import pytest
from unittest.mock import MagicMock, AsyncMock
from bot.commands.admin.events_admin import AdminEventCommands
from tests.helpers import invoke_app_command


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.basic
@pytest.mark.asyncio
async def test_delete_event_success(monkeypatch, mock_interaction):
    """Deletes an event successfully after confirmation."""
    cog = AdminEventCommands(bot=None)

    fake_event = MagicMock()
    fake_event.event_name = "Test Event"

    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", lambda *a, **k: fake_event)
    monkeypatch.setattr("bot.commands.admin.events_admin.confirm_action", AsyncMock(return_value=True))
    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.delete_event", lambda *a, **k: True)

    await invoke_app_command(
        cog.delete_event,
        cog,
        mock_interaction,
        shortcode="t_event",
        reason="Testing delete"
    )

    mock_interaction.edit_original_response.assert_awaited_with(
        content=f"✅ Event `Test Event` deleted.", 
        view=None
    )


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_delete_event_not_found(monkeypatch, mock_interaction):
    """Fails if the event is not found."""
    cog = AdminEventCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", lambda *a, **k: None)

    await invoke_app_command(
        cog.delete_event,
        cog,
        mock_interaction,
        shortcode="missing",
        reason="Testing delete"
    )

    mock_interaction.edit_original_response.assert_awaited_with(
        content="❌ Event `missing` not found.",
        view=None
    )


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_delete_event_cancelled(monkeypatch, mock_interaction):
    """Does not delete if confirmation is declined."""
    cog = AdminEventCommands(bot=None)

    fake_event = MagicMock()
    fake_event.event_name = "Test Event"

    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", lambda *a, **k: fake_event)
    monkeypatch.setattr("bot.commands.admin.events_admin.confirm_action", AsyncMock(return_value=False))
    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.delete_event", lambda *a, **k: pytest.fail("delete_event should not be called"))

    await invoke_app_command(
        cog.delete_event,
        cog,
        mock_interaction,
        shortcode="t_event",
        reason="Testing delete"
    )

    mock_interaction.edit_original_response.assert_awaited_with(
        content="❌ Deletion cancelled or timed out.", 
        view=None
    )


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_delete_event_missing_reason(monkeypatch, mock_interaction):
    """Fails if no reason is provided."""
    cog = AdminEventCommands(bot=None)

    fake_event = MagicMock()
    fake_event.event_name = "Test Event"

    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", lambda *a, **k: fake_event)
    # Prevent hanging on confirmation
    monkeypatch.setattr("bot.commands.admin.events_admin.confirm_action", AsyncMock(return_value=False))

    await invoke_app_command(
        cog.delete_event,
        cog,
        mock_interaction,
        shortcode="t_event",
        reason=None
    )

    mock_interaction.edit_original_response.assert_awaited_with(
        content="❌ Deletion cancelled or timed out.", 
        view=None
    )