import pytest
from unittest.mock import MagicMock
from bot.commands.admin.events_admin import AdminEventCommands
from tests.helpers import invoke_app_command


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.basic
@pytest.mark.asyncio
async def test_create_event_success(monkeypatch, mock_interaction):
    """Creates event successfully when valid input."""
    cog = AdminEventCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", lambda *a, **k: None)
    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.create_event", lambda *a, **k: MagicMock(event_name="Test Event"))

    await invoke_app_command(
        cog.create_event,
        cog,
        mock_interaction,
        shortcode="test",
        name="Test Event",
        description="An example event",
        start_date="2025-08-10"
    )

    mock_interaction.followup.send.assert_awaited()
    sent_message = mock_interaction.followup.send.await_args[1].get("content", "")
    assert "✅ Event `Test Event` created with shortcode `test2508`." in sent_message
    assert "*(defaulted to you)*" in sent_message


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.basic
@pytest.mark.asyncio
async def test_create_event_success_with_coordinator(monkeypatch, mock_interaction):
    """Creates event successfully when coordinator is specified (no default-to-you note)."""
    cog = AdminEventCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", lambda *a, **k: None)
    monkeypatch.setattr(
        "bot.commands.admin.events_admin.events_crud.create_event",
        lambda *a, **k: MagicMock(event_name="Test Event")
    )

    # Fake coordinator like a Discord Member/User
    fake_coordinator = MagicMock()
    fake_coordinator.id = 999999999999999999

    await invoke_app_command(
        cog.create_event,
        cog,
        mock_interaction,
        shortcode="test",
        name="Test Event",
        description="An example event",
        start_date="2025-08-10",
        end_date="2025-08-15",
        coordinator=fake_coordinator,
        tags="tag1, tag2",
        message_link="https://discord.com/channels/1/2/3",
        role_id="123456789012345678"
    )

    mock_interaction.followup.send.assert_awaited()
    sent_message = mock_interaction.followup.send.await_args[1].get("content", "")
    assert "✅ Event `Test Event` created with shortcode `test2508`." in sent_message
    assert "*(defaulted to you)*" not in sent_message


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_create_event_already_exists(monkeypatch, mock_interaction):
    """Fails if event with same shortcode already exists."""
    cog = AdminEventCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", lambda *a, **k: MagicMock())

    await invoke_app_command(
        cog.create_event,
        cog,
        mock_interaction,
        shortcode="dup",
        name="Duplicate Event",
        description="Already in DB",
        start_date="2025-08-10",
        end_date="2025-08-15"
    )

    mock_interaction.followup.send.assert_awaited_with(
        "❌ An event with shortcode `dup2508` already exists. Choose a different shortcode or start date."
    )


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_create_event_invalid_start_date(monkeypatch, mock_interaction):
    """Fails if start date format is invalid."""
    cog = AdminEventCommands(bot=None)
    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", lambda *a, **k: None)

    await invoke_app_command(
        cog.create_event,
        cog,
        mock_interaction,
        shortcode="badstart",
        name="Bad Start",
        description="Invalid start date",
        start_date="not-a-date",
        end_date="2025-08-15"
    )

    mock_interaction.followup.send.assert_awaited_with("❌ Invalid start date format. Use YYYY-MM-DD.")


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_create_event_invalid_end_date(monkeypatch, mock_interaction):
    """Fails if end date format is invalid."""
    cog = AdminEventCommands(bot=None)
    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", lambda *a, **k: None)

    await invoke_app_command(
        cog.create_event,
        cog,
        mock_interaction,
        shortcode="badend",
        name="Bad End",
        description="Invalid end date",
        start_date="2025-08-10",
        end_date="invalid-date"
    )

    mock_interaction.followup.send.assert_awaited_with("❌ Invalid end date format. Use YYYY-MM-DD or leave empty.")


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_create_event_negative_priority(monkeypatch, mock_interaction):
    """Fails if priority is negative."""
    cog = AdminEventCommands(bot=None)
    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", lambda *a, **k: None)

    await invoke_app_command(
        cog.create_event,
        cog,
        mock_interaction,
        shortcode="negprio",
        name="Negative Priority",
        description="Testing negative",
        start_date="2025-08-10",
        end_date="2025-08-15",
        priority=-1
    )

    mock_interaction.followup.send.assert_awaited_with("❌ Priority must be a non-negative integer.")