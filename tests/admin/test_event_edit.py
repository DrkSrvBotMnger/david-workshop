import pytest
from unittest.mock import MagicMock
from bot.commands.admin.events_admin import AdminEventCommands
from tests.helpers import invoke_app_command


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.basic
@pytest.mark.asyncio
async def test_edit_event_success(monkeypatch, mock_interaction):
    """Edits an event successfully when valid changes are provided."""
    cog = AdminEventCommands(bot=None)

    # The same mock object will be used for get_event_by_key and updated in place
    fake_event = MagicMock()
    fake_event.event_name = "Old Event"

    def fake_get_event_by_key(*a, **k):
        return fake_event

    def fake_update_event(*a, **k):
        # Directly mutate the same mock the command is holding
        new_name = k.get("event_update_data", {}).get("event_name")
        if new_name:
            fake_event.event_name = new_name
        return fake_event  # just like real update_event returns the updated event

    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", fake_get_event_by_key)
    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.update_event", fake_update_event)

    await invoke_app_command(
        cog.edit_event,
        cog,
        mock_interaction,
        shortcode="editme",
        name="New Event Name"
    )

    mock_interaction.followup.send.assert_awaited()
    args, kwargs = mock_interaction.followup.send.await_args
    sent_message = args[0] if args else kwargs.get("content", "")
    assert "✅ Event `New Event Name (editme)` updated successfully." in sent_message


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_edit_event_success_with_clear_and_reason(monkeypatch, mock_interaction):
    """Edits an event successfully when valid changes are provided."""
    cog = AdminEventCommands(bot=None)

    # The same mock object will be used for get_event_by_key and updated in place
    fake_event = MagicMock()
    fake_event.event_name = "Event Name"
    fake_event.tags = "darklina, freeform"
    fake_event.end_date = "2025-04-20"

    def fake_get_event_by_key(*a, **k):
        return fake_event

    def fake_update_event(*a, **k):
        # Directly mutate the same mock the command is holding
        new_name = k.get("event_update_data", {}).get("event_name")
        if new_name:
            fake_event.event_name = new_name
        return fake_event  # just like real update_event returns the updated event

    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", fake_get_event_by_key)
    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.update_event", fake_update_event)

    await invoke_app_command(
        cog.edit_event,
        cog,
        mock_interaction,
        shortcode="editme",
        end_date="CLEAR",
        tags="CLEAR",
        reason="Testing edit with CLEAR"
    )

    mock_interaction.followup.send.assert_awaited()
    args, kwargs = mock_interaction.followup.send.await_args
    sent_message = args[0] if args else kwargs.get("content", "")
    assert "✅ Event `Event Name (editme)` updated successfully." in sent_message
    assert "📝 Reason: Testing edit with CLEAR" in sent_message


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_edit_event_not_found(monkeypatch, mock_interaction):
    """Fails if the event does not exist."""
    cog = AdminEventCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", lambda *a, **k: None)

    await invoke_app_command(
        cog.edit_event,
        cog,
        mock_interaction,
        shortcode="missing",
        name="Should Not Matter"
    )

    mock_interaction.followup.send.assert_awaited_with("❌ Event `missing` not found.")


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_edit_event_invalid_start_date(monkeypatch, mock_interaction):
    """Fails if the start date is invalid."""
    cog = AdminEventCommands(bot=None)

    fake_event = MagicMock()
    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", lambda *a, **k: fake_event)

    await invoke_app_command(
        cog.edit_event,
        cog,
        mock_interaction,
        shortcode="invalidstart",
        start_date="bad-date"
    )

    mock_interaction.followup.send.assert_awaited_with("❌ Invalid start date format. Use YYYY-MM-DD.")


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_edit_event_invalid_end_date(monkeypatch, mock_interaction):
    """Fails if the end date is invalid."""
    cog = AdminEventCommands(bot=None)

    fake_event = MagicMock()
    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", lambda *a, **k: fake_event)

    await invoke_app_command(
        cog.edit_event,
        cog,
        mock_interaction,
        shortcode="invalidend",
        end_date="not-a-date"
    )

    mock_interaction.followup.send.assert_awaited_with("❌ Invalid end date format. Use YYYY-MM-DD or CLEAR to remove it.")


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_edit_event_no_valid_fields(monkeypatch, mock_interaction):
    """Fails if no valid fields are provided."""
    cog = AdminEventCommands(bot=None)

    fake_event = MagicMock()
    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", lambda *a, **k: fake_event)

    await invoke_app_command(
        cog.edit_event,
        cog,
        mock_interaction,
        shortcode="novalues"
    )

    mock_interaction.followup.send.assert_awaited_with("❌ No valid fields provided to update.")