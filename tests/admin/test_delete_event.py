import pytest
import os
from db.schema import Base
from sqlalchemy import create_engine
from unittest.mock import AsyncMock, patch
from bot.commands.admin.events_admin import AdminEventCommands

# Engine pointing to your test DB
engine = create_engine(os.environ["DATABASE_URL_TEST"])

@pytest.fixture(scope="module", autouse=True)
def clean_up_after_file():
    yield  # Run tests first
    # Clean up DB afterwards
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())

@pytest.fixture
def mock_interaction():
    mock = AsyncMock()
    mock.user.id = 1234
    mock.user.mention = "<@1234>"
    mock.response.defer = AsyncMock()
    mock.followup.send = AsyncMock()
    mock.guild.get_channel = AsyncMock(return_value=AsyncMock(send=AsyncMock()))
    return mock


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.asyncio
async def test_delete_event_success_message(mock_interaction, test_session, seed_user_and_event):
    # Seed DB with a non-active, non-visible event
    event = seed_user_and_event(test_session, event_id="delete_me")
    event.active = False
    event.visible = False
    test_session.commit()

    admin_cmds = AdminEventCommands(bot=None)
    event_name = event.name

    # Patch confirm_action to always confirm
    with patch("bot.commands.admin.events_admin.confirm_action", new_callable=AsyncMock, return_value=True):
        await admin_cmds.delete_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            event_id="delete_me",
            reason="Obsolete"
        )
    mock_interaction.edit_original_response.assert_called_with(
        content=f"✅ Event `{event_name}` deleted.",
        view=None
    )


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_delete_event_not_found(mock_interaction, test_session):
    admin_cmds = AdminEventCommands(bot=None)

    with patch("bot.commands.admin.events_admin.confirm_action", new_callable=AsyncMock, return_value=True):
        await admin_cmds.delete_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            event_id="nope",
            reason="Obsolete"
        )
    mock_interaction.edit_original_response.assert_called_with(
        content="❌ Event `nope` not found."
    )


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.asyncio
async def test_delete_event_active_blocked(mock_interaction, test_session, seed_user_and_event):
    event = seed_user_and_event(test_session, event_id="active_event")
    event.active = True
    test_session.commit()

    admin_cmds = AdminEventCommands(bot=None)

    await admin_cmds.delete_event.callback(
        admin_cmds,
        interaction=mock_interaction,
        event_id="active_event",
        reason="Maintenance"
    )
    mock_interaction.edit_original_response.assert_called_with(
        content="⚠️ Cannot delete an event that is active or visible. Please deactivate/hide it first."
    )


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.asyncio
async def test_delete_event_visible_blocked(mock_interaction, test_session, seed_user_and_event):
    event = seed_user_and_event(test_session, event_id="visible_event")
    event.visible = True
    test_session.commit()

    admin_cmds = AdminEventCommands(bot=None)

    await admin_cmds.delete_event.callback(
        admin_cmds,
        interaction=mock_interaction,
        event_id="visible_event",
        reason="Maintenance"
    )
    mock_interaction.edit_original_response.assert_called_with(
        content="⚠️ Cannot delete an event that is active or visible. Please deactivate/hide it first."
    )


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.asyncio
async def test_delete_event_logs_action(mock_interaction, test_session, seed_user_and_event):
    event = seed_user_and_event(test_session, event_id="log_me")
    event.active = False
    event.visible = False
    test_session.commit()

    admin_cmds = AdminEventCommands(bot=None)

    with patch("bot.crud.general_crud.log_change") as mock_log, \
         patch("bot.commands.admin.events_admin.confirm_action", new_callable=AsyncMock, return_value=True):
        await admin_cmds.delete_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            event_id="log_me",
            reason="Test logging"
        )

        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert kwargs["action"] == "delete"
        assert "Test logging" in kwargs["description"]
        assert kwargs["performed_by"] == str(mock_interaction.user.id)