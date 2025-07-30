import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bot.commands.admin.events_admin import AdminEventCommands


@pytest.fixture
def mock_interaction():
    mock = MagicMock()
    mock.user.id = 1234
    mock.user.mention = "<@1234>"
    mock.response.defer = AsyncMock()
    mock.followup.send = AsyncMock()
    mock.guild.get_channel = MagicMock(return_value=AsyncMock(send=AsyncMock()))
    return mock


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.asyncio
async def test_create_event_success_message(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)

    mock_created_event = MagicMock()
    mock_created_event.name = "Test Event"

    with patch("bot.crud.events_crud.get_event", return_value=None), \
         patch("bot.crud.events_crud.create_event", return_value=mock_created_event):

        await admin_cmds.create_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            shortcode="testevent",
            name="Test Event",
            description="desc",
            start_date="2025-08-01",
            end_date=None,
            coordinator=None,
            tags=None,
            embed_channel=None,
            embed_message_id=None,
            role_id=None,
            priority=0,
            shop_section_id=None
        )

        mock_interaction.followup.send.assert_called_once_with(
            content="✅ Event `Test Event` created with ID `testevent_2025_08`.\n👤 Coordinator: <@1234> *(defaulted to you)*"
        )


@pytest.mark.admin
@pytest.mark.asyncio
async def test_create_event_invalid_start_date(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)

    await admin_cmds.create_event.callback(
        admin_cmds,
        interaction=mock_interaction,
        shortcode="testevent",
        name="Test Event",
        description="desc",
        start_date="invalid-date",
        end_date=None,
        coordinator=None,
        tags=None,
        embed_channel=None,
        embed_message_id=None,
        role_id=None,
        priority=0,
        shop_section_id=None
    )

    mock_interaction.followup.send.assert_called_once_with(
        "❌ Invalid start date format. Use YYYY-MM-DD."
    )


@pytest.mark.admin
@pytest.mark.asyncio
async def test_create_event_invalid_end_date(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)

    await admin_cmds.create_event.callback(
        admin_cmds,
        interaction=mock_interaction,
        shortcode="testevent",
        name="Test Event",
        description="desc",
        start_date="2025-08-01",
        end_date="not-a-date",
        coordinator=None,
        tags=None,
        embed_channel=None,
        embed_message_id=None,
        role_id=None,
        priority=0,
        shop_section_id=None
    )

    mock_interaction.followup.send.assert_called_once_with(
        "❌ Invalid end date format. Use YYYY-MM-DD or leave empty."
    )


@pytest.mark.admin
@pytest.mark.asyncio
async def test_create_event_duplicate_event_id(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)

    mock_event = MagicMock()
    with patch("bot.crud.events_crud.get_event", return_value=mock_event):
        await admin_cmds.create_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            shortcode="testevent",
            name="Test Event",
            description="desc",
            start_date="2025-08-01",
            end_date=None,
            coordinator=None,
            tags=None,
            embed_channel=None,
            embed_message_id=None,
            role_id=None,
            priority=0,
            shop_section_id=None
        )

        mock_interaction.followup.send.assert_called_once_with(
            "❌ An event with ID `testevent_2025_08` already exists. Choose a different shortcode or start date."
        )


@pytest.mark.admin
@pytest.mark.asyncio
async def test_create_event_default_coordinator_embed_event_id(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)

    with patch("bot.crud.events_crud.get_event", return_value=None), \
     patch("bot.crud.events_crud.create_event") as mock_create, \
     patch("bot.commands.admin.events_admin.EMBED_CHANNEL_ID", new="999999999"):

        await admin_cmds.create_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            shortcode="testevent",
            name="Test Event",
            description="desc",
            start_date="2025-08-01",
            end_date=None,
            coordinator=None,
            tags=None,
            embed_channel=None,
            embed_message_id=None,
            role_id=None,
            priority=0,
            shop_section_id=None
        )

    assert mock_create.called
    args, kwargs = mock_create.call_args
    assert kwargs["coordinator_id"] == str(mock_interaction.user.id)
    assert kwargs["embed_channel_id"] == "999999999"
    assert kwargs["event_id"] == "testevent_2025_08"


@pytest.mark.admin
@pytest.mark.asyncio
async def test_create_event_embed_channel_argument(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)

    mock_channel = MagicMock()
    mock_channel.id = 777777777

    with patch("bot.crud.events_crud.get_event", return_value=None), \
         patch("bot.crud.events_crud.create_event") as mock_create:

        await admin_cmds.create_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            shortcode="channelevent",
            name="Event with Channel",
            description="desc",
            start_date="2025-08-01",
            end_date=None,
            coordinator=None,
            tags=None,
            embed_channel=mock_channel,
            embed_message_id=None,
            role_id=None,
            priority=0,
            shop_section_id=None
        )

        assert mock_create.called
        _, kwargs = mock_create.call_args
        assert kwargs["embed_channel_id"] == str(mock_channel.id)


@pytest.mark.admin
@pytest.mark.asyncio
async def test_create_event_tags_trimmed(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)

    with patch("bot.crud.events_crud.get_event", return_value=None), \
         patch("bot.crud.events_crud.create_event") as mock_create:

        await admin_cmds.create_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            shortcode="tagtest",
            name="Tag Event",
            description="desc",
            start_date="2025-08-01",
            end_date=None,
            coordinator=None,
            tags="  halloween ,  rp  ",
            embed_channel=None,
            embed_message_id=None,
            role_id=None,
            priority=0,
            shop_section_id=None
        )

        assert mock_create.called
        _, kwargs = mock_create.call_args
        assert kwargs["tags"] == "halloween ,  rp"


@pytest.mark.admin
@pytest.mark.asyncio 
async def test_create_event_invalid_priority(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)
    with patch("bot.crud.events_crud.get_event", return_value=None):
        await admin_cmds.create_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            shortcode="badpriority",
            name="Bad Priority Event",
            description="desc",
            start_date="2025-08-01",
            end_date=None,
            coordinator=None,
            tags=None,
            embed_channel=None,
            embed_message_id=None,
            role_id=None,
            priority=-5,
            shop_section_id=None
        )

    mock_interaction.followup.send.assert_called_once_with(
        "❌ Priority must be a non-negative integer."
    )


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.asyncio
async def test_create_event_logs_action(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)

    with patch("bot.crud.events_crud.get_event", return_value=None), \
         patch("bot.crud.general_crud.log_event_change") as mock_log, \
         patch("bot.config.EMBED_CHANNEL_ID", new="123456789"):

        await admin_cmds.create_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            shortcode="logged",
            name="Logged Event",
            description="An event to test logging.",
            start_date="2025-08-01",
            end_date=None,
            coordinator=None,
            tags=None,
            embed_channel=None,
            embed_message_id=None,
            role_id=None,
            priority=0,
            shop_section_id=None
        )

        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        print("CALL ARGS:", mock_log.call_args)

        mock_log.assert_called_once()
        _, kwargs = mock_log.call_args
        assert kwargs["action"] == "create"
        assert kwargs["performed_by"] == str(mock_interaction.user.id)
        assert "Event Logged Event(logged_2025_08) created." in kwargs["description"]