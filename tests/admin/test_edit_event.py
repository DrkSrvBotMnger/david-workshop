import os
import pytest
from sqlalchemy import create_engine
from db.schema import Base
from unittest.mock import AsyncMock, MagicMock, patch
from bot.commands.admin.events_admin import AdminEventCommands
import bot.crud.events_crud
from db.database import db_session
from db.schema import Event
from datetime import datetime

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
    mock = MagicMock()
    mock.user.id = 1234
    mock.user.mention = "<@1234>"
    mock.response.defer = AsyncMock()
    mock.followup.send = AsyncMock()
    mock.guild.get_channel = MagicMock(return_value=AsyncMock(send=AsyncMock()))
    return mock


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.asyncio
async def test_editevent_all_fields_updated(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)
    mock_event = MagicMock(active=False, visible=False)

    with patch("bot.crud.events_crud.get_event", return_value=mock_event), \
         patch("bot.crud.events_crud.update_event", return_value=True):

        await admin_cmds.edit_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            event_id="test",
            name="Updated Name",
            description="Updated Desc",
            start_date="2025-08-10",
            end_date="2025-08-20",
            coordinator=MagicMock(id=4321),
            tags="new, test",
            embed_channel=MagicMock(id=1111),
            embed_message_id="55555",
            role_id=MagicMock(id=9999),
            priority="10",
            shop_section_id="shop123",
            reason="Full update"
        )

        mock_interaction.followup.send.assert_called()


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.asyncio
async def test_editevent_clear_fields(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)
    mock_event = MagicMock(active=False, visible=False)

    with patch("bot.crud.events_crud.get_event", return_value=mock_event), \
         patch("bot.crud.events_crud.update_event", return_value=True):

        await admin_cmds.edit_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            event_id="test",
            end_date="CLEAR",
            tags="CLEAR",
            role_id="CLEAR",
            shop_section_id="CLEAR",
            embed_message_id="CLEAR"
        )

        mock_interaction.followup.send.assert_called()


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.asyncio
async def test_edit_event_clear_priority_sets_zero(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)
    mock_event = MagicMock(active=False, visible=False)

    with patch("bot.crud.events_crud.get_event", return_value=mock_event), \
         patch("bot.crud.events_crud.update_event") as mock_update:

        await admin_cmds.edit_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            event_id="test",
            priority="CLEAR"
        )

        mock_update.assert_called_once()
        _, kwargs = mock_update.call_args
        assert kwargs["priority"] == 0


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_editevent_reason_in_confirmation(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)
    mock_event = MagicMock(active=False, visible=False, event_id="event123")
    mock_event.name = "Renamed"  # Simulate that the update changed the name

    with patch("bot.crud.events_crud.get_event", return_value=mock_event), \
         patch("bot.crud.events_crud.update_event", return_value=True):

        await admin_cmds.edit_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            event_id="event123",
            name="Renamed",
            reason="Fix typo"
        )

        mock_interaction.followup.send.assert_called_once()
        args, kwargs = mock_interaction.followup.send.call_args
        assert "✅ Event `Renamed (event123)` updated successfully." in args[0]
        assert "📝 Reason: Fix typo" in args[0]


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_editevent_no_fields_provided(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)
    mock_event = MagicMock(active=False, visible=False)

    with patch("bot.crud.events_crud.get_event", return_value=mock_event):
        await admin_cmds.edit_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            event_id="test",
            reason="Does nothing"
        )

        mock_interaction.followup.send.assert_called_with("❌ No valid fields provided to update.")


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.asyncio
async def test_editevent_populates_modified_by_and_at(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)
    mock_event = MagicMock(active=False, visible=False)

    with patch("bot.crud.events_crud.get_event", return_value=mock_event), \
         patch("bot.crud.events_crud.update_event") as mock_update:

        await admin_cmds.edit_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            event_id="test",
            name="Update"
        )

        mock_update.assert_called_once()
        _, kwargs = mock_update.call_args
        assert kwargs["modified_by"] == str(mock_interaction.user.id)
        assert "modified_at" in kwargs


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_editevent_invalid_start_date(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)

    await admin_cmds.edit_event.callback(
        admin_cmds,
        interaction=mock_interaction,
        event_id="test",
        start_date="not-a-date"
    )

    mock_interaction.followup.send.assert_called_with("❌ Invalid start date format. Use YYYY-MM-DD.")


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_editevent_invalid_end_date(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)

    await admin_cmds.edit_event.callback(
        admin_cmds,
        interaction=mock_interaction,
        event_id="test",
        end_date="not-a-date"
    )

    mock_interaction.followup.send.assert_called_with("❌ Invalid end date format. Use YYYY-MM-DD or CLEAR to remove it.")


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_editevent_event_not_found(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)

    with patch("bot.crud.events_crud.get_event", return_value=None):
        await admin_cmds.edit_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            event_id="missing"
        )

        mock_interaction.followup.send.assert_called_with("❌ Event `missing` not found.")


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.asyncio
async def test_editevent_block_if_active(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)
    mock_event = MagicMock(active=True)

    with patch("bot.crud.events_crud.get_event", return_value=mock_event):
        await admin_cmds.edit_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            event_id="active_event",
            name="New name"
        )

        mock_interaction.followup.send.assert_called_with(
            "⚠️ This event is active and cannot be edited. Use a separate command to deactivate it first."
        )


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.asyncio
async def test_editevent_block_clear_embed_message_if_visible(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)
    mock_event = MagicMock(active=False, visible=True)

    with patch("bot.crud.events_crud.get_event", return_value=mock_event):
        await admin_cmds.edit_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            event_id="visible_event",
            embed_message_id="CLEAR"
        )

        mock_interaction.followup.send.assert_called_with(
            "❌ You cannot remove the embed message ID while the event is visible. Hide it first."
        )


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_edit_event_embed_channel_and_message_id(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)
    mock_event = MagicMock(active=False, visible=False)

    mock_channel = MagicMock()
    mock_channel.id = 888888

    with patch("bot.crud.events_crud.get_event", return_value=mock_event), \
         patch("bot.crud.events_crud.update_event") as mock_update:

        await admin_cmds.edit_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            event_id="test_event",
            embed_channel=mock_channel,
            embed_message_id="999999"
        )

        _, kwargs = mock_update.call_args
        assert kwargs["embed_channel_id"] == "888888"
        assert kwargs["embed_message_id"] == "999999"


@pytest.mark.admin
@pytest.mark.event
@pytest.mark.asyncio
async def test_edit_event_tags_are_trimmed(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)
    mock_event = MagicMock(active=False, visible=False)

    with patch("bot.crud.events_crud.get_event", return_value=mock_event), \
         patch("bot.crud.events_crud.update_event") as mock_update:

        await admin_cmds.edit_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            event_id="test_event",
            tags="  lore,  character ,  action  "
        )

        mock_update.assert_called_once()
        _, kwargs = mock_update.call_args
        assert kwargs["tags"] == "lore,character,action"


@pytest.mark.admin
@pytest.mark.basic
@pytest.mark.event
@pytest.mark.asyncio
async def test_edit_event_logs_action(mock_interaction):
    admin_cmds = AdminEventCommands(bot=None)

    # 1️⃣ Create a real event in the test DB
    with db_session() as session:
        event = Event(
            event_id="editable123",
            name="Original Event",
            description="For testing edit",
            type="freeform",
            start_date="2025-01-01",
            end_date=None,
            created_by="Tester",
            created_at=str(datetime.utcnow()),
            coordinator_id="Tester",
            active=False,
            visible=False
        )
        session.add(event)
        session.commit()
        event_id = event.event_id
        db_id = event.id  # this is what log_change will use

    # 2️⃣ Patch only log_change so we can assert the call
    with patch("bot.commands.admin.events_admin.general_crud.log_change") as mock_log:
        await admin_cmds.edit_event.callback(
            admin_cmds,
            interaction=mock_interaction,
            event_id=event_id,
            name="Edited Event",
            reason="Fixed naming"
        )

        # 3️⃣ Assert the logger was called once with correct args
        mock_log.assert_called_once()
        _, kwargs = mock_log.call_args
        assert kwargs["action"] == "edit"
        assert kwargs["fk_value"] == db_id
        assert kwargs["fk_field"] == "event_id"
        assert kwargs["performed_by"] == str(mock_interaction.user.id)
        assert kwargs["description"] == "Event Edited Event (editable123) updated. Reason: Fixed naming"

    # 4️⃣ Verify DB actually changed
    with db_session() as session:
        updated_event = bot.crud.events_crud.get_event(session, event_id)
        assert updated_event.name == "Edited Event"
