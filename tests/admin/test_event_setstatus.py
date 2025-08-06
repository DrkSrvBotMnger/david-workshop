import pytest
from unittest.mock import MagicMock, AsyncMock
from bot.commands.admin.events_admin import AdminEventCommands
from tests.helpers import invoke_app_command
from db.schema import EventStatus


# Helper to simulate discord.app_commands.Choice[str]
class FakeChoice:
    def __init__(self, value):
        self.value = value

@pytest.mark.admin
@pytest.mark.event
@pytest.mark.basic
@pytest.mark.asyncio
async def test_setstatus_success(monkeypatch, mock_interaction):
    """Successfully updates event status."""
    cog = AdminEventCommands(bot=None)

    fake_event = MagicMock()
    fake_event.event_name = "Test Event"
    fake_event.event_status = EventStatus.visible
    fake_event.id = 123

    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", lambda *a, **k: fake_event)
    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.set_event_status", lambda *a, **k: fake_event)
    monkeypatch.setattr("bot.commands.admin.events_admin.post_announcement_message", AsyncMock())

    await invoke_app_command(
        cog.set_event_status,
        cog,
        mock_interaction,
        "t_event",
        FakeChoice("active")
    )

    mock_interaction.followup.send.assert_awaited_with(
        "✅ Event `Test Event (t_event)` status changed to **active**."
    )


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_setstatus_event_not_found(monkeypatch, mock_interaction):
    """Fails if the event is not found."""
    cog = AdminEventCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", lambda *a, **k: None)

    await invoke_app_command(
        cog.set_event_status,
        cog,
        mock_interaction,
        "missing",
        FakeChoice("active")
    )

    mock_interaction.followup.send.assert_awaited_with("❌ Event `missing` not found.")


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_setstatus_invalid_transition(monkeypatch, mock_interaction):
    """Fails if the transition is not allowed."""
    cog = AdminEventCommands(bot=None)

    fake_event = MagicMock()
    fake_event.event_name = "Test Event"
    fake_event.event_status = EventStatus.archived # can't go from archived to active

    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", lambda *a, **k: fake_event)

    await invoke_app_command(
        cog.set_event_status,
        cog,
        mock_interaction,
        "t_event",
        FakeChoice("active")
    )

    mock_interaction.followup.send.assert_awaited()
    args, kwargs = mock_interaction.followup.send.await_args
    sent_message = args[0] if args else kwargs.get("content", "")
    assert "❌ Cannot move from archived to active." in sent_message


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_setstatus_missing_embed_for_visible(monkeypatch, mock_interaction):
    """Fails if making event visible but embed is missing."""
    cog = AdminEventCommands(bot=None)

    fake_event = MagicMock()
    fake_event.event_name = "Test Event"
    fake_event.event_status = EventStatus.draft
    fake_event.id = 123
    fake_event.embed_message_discord_id = None
    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", lambda *a, **k: fake_event)
    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.set_event_status", lambda *a, **k: fake_event)
    
    await invoke_app_command(
        cog.set_event_status,
        cog,
        mock_interaction,
        "t_event",
        FakeChoice("visible")
    )

    mock_interaction.followup.send.assert_awaited_with(
        "❌ You must define the embed message before making an event visible."
    )


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_setstatus_posts_announcement(monkeypatch, mock_interaction):
    """Posts announcement when moving to active/visible with embed."""
    cog = AdminEventCommands(bot=None)

    # Use a proper fake event object with realistic values
    fake_event = MagicMock()
    fake_event.event_name = "Test Event"
    fake_event.event_status = EventStatus.draft
    fake_event.embed_message_id = 12345
    fake_event.id = 123  # So DB logging doesn't choke on MagicMock

    # get_event_by_key returns our fake_event
    monkeypatch.setattr(
        "bot.commands.admin.events_admin.events_crud.get_event_by_key",
        lambda *a, **k: fake_event
    )
    # set_event_status returns the updated event, not True
    monkeypatch.setattr(
        "bot.commands.admin.events_admin.events_crud.set_event_status",
        lambda *a, **k: fake_event
    )
    # Patch announcement method so we can check if it was called
    post_mock = AsyncMock()
    monkeypatch.setattr(
        "bot.commands.admin.events_admin.post_announcement_message",
        post_mock
    )

    await invoke_app_command(
        cog.set_event_status,
        cog,
        mock_interaction,
        "t_event",
        FakeChoice("visible")
    )

    post_mock.assert_awaited()