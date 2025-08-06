import pytest
from unittest.mock import MagicMock, AsyncMock
from bot.commands.admin.events_admin import AdminEventCommands
from tests.helpers import invoke_app_command


# ===== LIST =====
@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_event_list_no_events(monkeypatch, mock_interaction):
    """Sends 'no events' message if DB is empty."""
    cog = AdminEventCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_all_events", lambda *a, **k: [])
    monkeypatch.setattr("bot.commands.admin.events_admin.paginate_embeds", AsyncMock())

    await invoke_app_command(
        cog.list_events,
        cog,
        mock_interaction
    )

    mock_interaction.followup.send.assert_awaited_with("❌ No events found with the given filters.")


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.basic
@pytest.mark.asyncio
async def test_event_list_with_results(monkeypatch, mock_interaction):
    """Calls paginate_embeds when events exist."""
    cog = AdminEventCommands(bot=None)

    fake_event = MagicMock()
    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_all_events", lambda *a, **k: [fake_event])
    pag_mock = AsyncMock()
    monkeypatch.setattr("bot.commands.admin.events_admin.paginate_embeds", pag_mock)

    await invoke_app_command(
        cog.list_events,
        cog,
        mock_interaction
    )

    pag_mock.assert_awaited()


# ===== SHOW =====
@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_show_event_not_found(monkeypatch, mock_interaction):
    """Sends error if event is missing."""
    cog = AdminEventCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", lambda *a, **k: None)

    await invoke_app_command(
        cog.show_event,
        cog,
        mock_interaction,
        shortcode="missing_event"
    )

    mock_interaction.followup.send.assert_awaited_with("❌ Event `missing_event` not found.")


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.basic
@pytest.mark.asyncio
async def test_show_event_success(monkeypatch, mock_interaction):
    """Builds and sends an event embed when found."""
    cog = AdminEventCommands(bot=None)

    fake_event = MagicMock()
    fake_event.event_name = "Test Event"
    fake_event.event_key = "t_event"

    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_by_key", lambda *a, **k: fake_event)

    await invoke_app_command(
        cog.show_event,
        cog,
        mock_interaction,
        shortcode="t_event"
    )

    mock_interaction.followup.send.assert_awaited()
    args, kwargs = mock_interaction.followup.send.await_args
    sent_embed = kwargs.get("embed") or (args[0] if args else None)
    assert sent_embed is not None, "Expected an embed to be sent"


# ===== LOGS =====
@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_event_logs_no_logs(monkeypatch, mock_interaction):
    """Sends error if no logs found."""
    cog = AdminEventCommands(bot=None)

    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_logs", lambda *a, **k: [])
    monkeypatch.setattr("bot.commands.admin.events_admin.paginate_embeds", AsyncMock())

    await invoke_app_command(
        cog.event_logs,
        cog,
        mock_interaction,
        "t_event"
    )

    mock_interaction.followup.send.assert_awaited_with("❌ No logs found with those filters.")


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.basic
@pytest.mark.asyncio
async def test_event_logs_with_results(monkeypatch, mock_interaction):
    """Calls paginate_embeds when logs exist."""
    cog = AdminEventCommands(bot=None)

    fake_log = MagicMock()
    monkeypatch.setattr("bot.commands.admin.events_admin.events_crud.get_event_logs", lambda *a, **k: [fake_log])
    pag_mock = AsyncMock()
    monkeypatch.setattr("bot.commands.admin.events_admin.paginate_embeds", pag_mock)

    await invoke_app_command(
        cog.event_logs,
        cog,
        mock_interaction,
        "t_event"
    )

    pag_mock.assert_awaited()
