import discord
from discord import app_commands, Interaction, Embed
from discord.ext import commands
from typing import Optional

from sqlalchemy.sql.base import _exclusive_against
from bot.crud import events_crud, action_events_crud, reward_events_crud
from bot.config import EVENT_ANNOUNCEMENT_CHANNEL_ID, EVENTS_PER_PAGE, LOGS_PER_PAGE
from bot.utils.time_parse_paginate import admin_or_mod_check, safe_parse_date, confirm_action, paginate_embeds, format_discord_timestamp, format_log_entry, parse_message_link, post_announcement_message
from db.database import db_session
from db.schema import EventLog, EventStatus
from bot.ui.admin.event_dashboard_view import EventDashboardView, build_event_embed


class AdminEventCommands(commands.GroupCog, name="admin_event"):
    """Admin commands for managing events."""
    def __init__(self, bot):
        self.bot = bot

    
    # === CREATE EVENT ===
    @admin_or_mod_check()
    @app_commands.describe(
        shortcode="Shortcode for the event (date auto-added: YYMM)",
        event_type="Type of event (by default freeform only for now)",
        name="Full name of the event",
        description="Public-facing description",
        start_date="Start date (YYYY-MM-DD)",
        end_date="End date (YYYY-MM-DD) (optional)",
        coordinator="Optional mod managing the event, defaults to you",
        priority="Order to display in listings (higher = higher)",
        tags="Comma-separated tags (e.g. rp, halloween) (optional)",
        message_link="Link to the message containing the display embed (optional)",
        role_id = "Discord role id to tag during announcements (optional)"
        )
    @app_commands.command(name="create", description="Create a new event.")
    async def create_event(
        self,
        interaction: discord.Interaction,
        shortcode: str,
        name: str,
        description: str,
        start_date: str,
        event_type: Optional[str] = "freeform",  # for now, only freeform events are supported]
        end_date: Optional[str] = None,
        coordinator: Optional[discord.Member] = None,
        priority: int = 0,
        tags: Optional[str] = None,
        message_link: Optional[str] = None,
        role_id: Optional[str] = None
    ):
        """Creates an event. Event key is auto-generated from shortcode + start month."""

        await interaction.response.defer(thinking=True, ephemeral=True)

        # TEMP: only freeform events are supported for now
        event_type = "freeform"
        
        # Handle date parsing
        start_date_parsed = safe_parse_date(start_date)
        if not start_date_parsed:
            await interaction.followup.send("❌ Invalid start date format. Use YYYY-MM-DD.")
            return
        if end_date:
            end_date_parsed = safe_parse_date(end_date)
            if not end_date_parsed:
                await interaction.followup.send("❌ Invalid end date format. Use YYYY-MM-DD or leave empty.")
                return
        else:
            end_date_parsed = None

        # Auto-generate event_key
        event_key = f"{shortcode.lower()}{start_date_parsed[2:4]}{start_date_parsed[5:7]}"

        # Handle coordinator
        if coordinator:
            coordinator_id = str(coordinator.id)
            coordinator_display = coordinator.mention
        else:
            coordinator_id = str(interaction.user.id)
            coordinator_display = interaction.user.mention

        # Handle tags and embed channel
        tag_str = tags.lower().strip() if tags else None
        
        if priority < 0:
            await interaction.followup.send("❌ Priority must be a non-negative integer.")
            return

        # Parse message link
        if message_link:
            embed_channel_discord_id, embed_message_discord_id = parse_message_link(message_link)
        else:
            embed_channel_discord_id = None
            embed_message_discord_id = None
        
        # Check for existing event_id then create event
        try:
            with db_session() as session:    
                existing_event = events_crud.get_event_by_key(
                    session=session, 
                    event_key=event_key
                )
                if existing_event:
                    await interaction.followup.send(
                        f"❌ An event with shortcode `{event_key}` already exists. Choose a different shortcode or start date."
                    )
                    return

                event_create_data ={
                    "event_key": event_key,
                    "event_name": name,
                    "event_type": event_type,
                    "event_description": description,
                    "start_date": start_date_parsed,
                    "end_date": end_date_parsed,
                    "created_by": str(interaction.user.id),
                    "coordinator_discord_id": coordinator_id,
                    "priority": priority,
                    "tags": tag_str,
                    "embed_channel_discord_id": embed_channel_discord_id,
                    "embed_message_discord_id": embed_message_discord_id,
                    "role_discord_id": role_id                    
                }
                    
                event = events_crud.create_event(
                    session=session,
                    event_create_data=event_create_data
                )
                
                # Extract now while session is open
                safe_event_name = event.event_name

        except Exception as e:
            print(f"❌ DB failure: {e}")
            await interaction.followup.send("❌ An unexpected error occurred.")
            return

        msg = f"✅ Event `{safe_event_name}` created with shortcode `{event_key}`.\n👤 Coordinator: {coordinator_display}"
        if not coordinator:
            msg += " *(defaulted to you)*"

        await interaction.followup.send(content=msg)


    # === EDIT EVENT ===
    @admin_or_mod_check()
    @app_commands.describe(
        shortcode="Shortcode of the event to edit",
        name="New full name (optional)",
        description="New description (optional)",
        start_date="New start date (YYYY-MM-DD)",
        end_date="New end date (YYYY-MM-DD, use CLEAR to remove)",
        coordinator="New coordinator (optional)",
        tags="New comma-separated tags (use CLEAR to remove)",
        priority="Updated display priority (use CLEAR to remove)",
        message_link="New message link to display (use CLEAR to remove)",
        role_id = "New discord role id to tag during announcements (use CLEAR to remove)",
        reason="Optional reason for editing (will be logged)"
    )
    @app_commands.command(name="edit", description="Edit an existing event's metadata.")
    async def edit_event(
        self,
        interaction: discord.Interaction,
        shortcode: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        coordinator: Optional[discord.Member] = None,
        tags: Optional[str] = None,
        priority: Optional[int] = None,
        message_link: Optional[str] = None,
        role_id: Optional[discord.Role] = None,
        reason: Optional[str] = None
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        # Check for existing event_id then update event
        with db_session() as session:
            event = events_crud.get_event_by_key(
                session=session, 
                event_key=shortcode    
            )
            if not event:
                await interaction.followup.send(f"❌ Event `{shortcode}` not found.")
                return

            # Prevent editing active events							   
            if event.event_status == EventStatus.active:
                await interaction.followup.send("⚠️ This event is active and cannot be edited. Use a separate command to deactivate it first.")
                return

    # Handle date parsing and CLEAR sentinel
            start_date_parsed = safe_parse_date(start_date) if start_date else None
            if start_date and not start_date_parsed:
                await interaction.followup.send("❌ Invalid start date format. Use YYYY-MM-DD.")
                return

            if end_date and end_date.strip().upper() != "CLEAR":
                end_date_parsed = safe_parse_date(end_date)
                if not end_date_parsed:
                     await interaction.followup.send("❌ Invalid end date format. Use YYYY-MM-DD or CLEAR to remove it.")
                     return
            else:
                end_date_parsed = None

            event_update_data = {}
            if name: 
                event_update_data["event_name"] = name
            if description: 
                event_update_data["event_description"] = description
            if start_date_parsed: 
                event_update_data["start_date"] = start_date_parsed
            if end_date:
                event_update_data["end_date"] = None if end_date.strip().upper() == "CLEAR" else end_date_parsed
            if coordinator: 
                event_update_data["coordinator_discord_id"] = str(coordinator.id)
            if tags:
                if tags.strip().upper() == "CLEAR":
                    event_update_data["tags"] = None
                else:
                    event_update_data["tags"] = ",".join(tag.strip() for tag in tags.split(","))            
            if message_link: 
                if message_link.strip().upper() == "CLEAR":
                    if event.event_status == EventStatus.visible:
                        await interaction.followup.send("❌ You cannot remove the embed message while the event is visible. Hide it first.")
                        return
                    event_update_data["embed_channel_discord_id"] = None
                    event_update_data["embed_message_discord_id"] = None
                else:
                    embed_channel_discord_id, embed_message_discord_id = parse_message_link(message_link)
                    event_update_data["embed_channel_discord_id"] = embed_channel_discord_id
                    event_update_data["embed_message_discord_id"] = embed_message_discord_id
            if role_id:
                if role_id.strip().upper() == "CLEAR":
                    event_update_data["role_discord_id"] = None 
                else: 
                    event_update_data["role_discord_id"] = role_id.strip()
            if priority:
                if priority.strip().upper() == "CLEAR":
                    event_update_data["priority"] = 0
                else:
                    try:
                        val = int(priority)
                        if val < 0:
                            raise ValueError
                        event_update_data["priority"] = val
                    except ValueError:
                        await interaction.followup.send("❌ Priority must be a non-negative integer or CLEAR.")
                        return

            if not event_update_data:
                await interaction.followup.send("❌ No valid fields provided to update.")
                return

            event_update_data["modified_by"] = str(interaction.user.id)
            
            events_crud.update_event(
                session=session,
                event_key=shortcode,
                event_update_data=event_update_data,
                reason=reason
            )

            # Extract now while session is open								   
            safe_event_name = event.event_name

        await interaction.followup.send(
            f"✅ Event `{safe_event_name} ({shortcode})` updated successfully." + (f"\n📝 Reason: {reason}" if reason else "")
        )


    # === DELETE EVENT ===
    @admin_or_mod_check()
    @app_commands.describe(
        shortcode="Shortcode of the event to delete",
        reason="Reason for deleting (will be logged)"
    )
    @app_commands.command(name="delete", description="Delete an event.")
    async def delete_event(
        self, 
        interaction: discord.Interaction, 
        shortcode: str, 
        reason: str
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            event = events_crud.get_event_by_key(
                session=session,
                event_key=shortcode
            )
            if not event:
                await interaction.edit_original_response(content=f"❌ Event `{shortcode}` not found.", view=None)
                return

            if event.event_status in (EventStatus.visible, EventStatus.active):
                await interaction.edit_original_response(content="⚠️ Cannot delete an event that is active or visible. Put the event in draft first.", view=None)
                return
            
            # Extract now while session is open
            safe_event_name = event.event_name

        # Ask for confirmation
        confirmed = await confirm_action(
            interaction=interaction, 
            item_name=f"event `{shortcode}` ({safe_event_name})", 
            item_action="delete",
            reason="Removal"
        )
        if not confirmed:
            await interaction.edit_original_response(content="❌ Deletion cancelled or timed out.", view=None)
            return

        with db_session() as session:
            event = events_crud.delete_event(
                session,
                event_key=shortcode,
                performed_by=str(interaction.user.id),
                reason=reason
            )
            if not event:
                await interaction.edit_original_response(content="❌ Event deletion failed unexpectedly.", view=None)
                return

        await interaction.edit_original_response(content=f"✅ Event `{safe_event_name}` deleted.", view=None)
    

    # === LIST EVENTS ===
    @admin_or_mod_check()
    @app_commands.describe(
        tag="Filter by tag (optional)",
        event_status="Filter by status",
        moderator="Only show events created or edited by this moderator"
    )
    @app_commands.choices(
        event_status=[
            app_commands.Choice(name="Draft", value="draft"),
            app_commands.Choice(name="Visible", value="visible"),
            app_commands.Choice(name="Active", value="active"),
            app_commands.Choice(name="Archived", value="archived")
        ]
    )
    @app_commands.command(name="list", description="List all events with filters")
    async def list_events(
        self,
        interaction: Interaction,
        tag: Optional[str] = None,
        event_status: Optional[app_commands.Choice[str]] = None,
        moderator: Optional[discord.User] = None,
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        mod_by_discord_id = str(moderator.id) if moderator else None
        status_value = event_status.value if event_status else None
        
        with db_session() as session:
            events = events_crud.get_all_events(
                session,
                tag=tag,
                event_status = status_value,
                mod_by_discord_id=mod_by_discord_id
            )

            if not events:
                await interaction.followup.send("❌ No events found with the given filters.")
                return
    
            pages = []
            for i in range(0, len(events), EVENTS_PER_PAGE):
                chunk = events[i:i+EVENTS_PER_PAGE]
                description_text = f"🔍 Tag: `{tag}`\n" if tag else  ""
                embed = Embed(title=f"🗂️ Events List ({i+1}-{i+len(chunk)}/{len(events)})", description=description_text)
                for e in chunk:
                    updated_by = f"<@{e.modified_by}>" if e.modified_by else f"<@{e.created_by}>"
                    formatted_time = format_discord_timestamp(e.modified_at or e.created_at)
                    lines = [
                        f"**Shortcode:** `{e.event_key}` | **Name:** {e.event_name}",
                        f"👤 Last updated by: {updated_by}",
                        f":timer: On: {formatted_time}",
                        f"📌 Status: {e.event_status.value.capitalize()} | 📎 Embed: {'✅' if e.embed_message_discord_id else '❌'} | 🎭 Role: {'✅' if e.role_discord_id else '❌'}",
                    ]
                    embed.add_field(name="\n", value="\n".join(lines), inline=False)
                pages.append(embed)
    
            await paginate_embeds(interaction, pages)



    # === SHOW EVENT METADATA ===
    @admin_or_mod_check()
    @app_commands.command(name="show", description="Display full metadata of a specific event.")
    async def show_event(self, interaction: Interaction, shortcode: str):
        await interaction.response.defer(ephemeral=True)

        with db_session() as session:
            # --- Get Event ---
            event = events_crud.get_event_by_key(session, event_key=shortcode)
            if not event:
                await interaction.followup.send(f"❌ Event `{shortcode}` not found.")
                return

            # --- Convert Event to dict ---
            event_data = {
                "event_name": event.event_name,
                "event_key": event.event_key,
                "start_date": event.start_date,
                "end_date": event.end_date,
                "tags": event.tags,
                "event_description": event.event_description,
                "created_by": event.created_by,
                "created_at": event.created_at,
                "modified_by": event.modified_by,
                "modified_at": event.modified_at,
                "priority": event.priority,
                "coordinator_discord_id": event.coordinator_discord_id,
                "role_discord_id": event.role_discord_id,
                "embed_message_discord_id": event.embed_message_discord_id,
                "embed_channel_discord_id": event.embed_channel_discord_id,
                "event_status": event.event_status.value,
                "event_type": event.event_type
            }

            # --- Get linked Actions ---
            action_events = action_events_crud.get_action_events_for_event(session, event.id)
            actions_data = []
            for ae in action_events:
                actions_data.append({
                    "action_key": ae.action.action_key if ae.action else None,
                    "variant": ae.variant,
                    "points_granted": ae.points_granted,
                    "reward_event_key": ae.reward_event.reward_event_key if ae.reward_event else None,
                    "is_allowed_during_visible": ae.is_allowed_during_visible,
                    "is_self_reportable": ae.is_self_reportable,
                    "input_help_text": ae.input_help_text
                })

            # --- Get linked Rewards ---
            reward_events = reward_events_crud.get_all_reward_events_for_event(session, event.id)
            rewards_data = []
            for re in reward_events:
                rewards_data.append({
"reward_name":re.reward.reward_name,
                    "reward_key": re.reward.reward_key if re.reward else None,
                    "price": re.price,
                    "availability": re.availability
                })

        # --- Create View ---
        guild_id = interaction.guild.id if interaction.guild else None
        view = EventDashboardView(event_data, actions_data, rewards_data, guild_id)

        # --- Send initial view ---
        await interaction.followup.send(embed=build_event_embed(event_data, guild_id), view=view)


    # === EVENT LOGS ===
    @admin_or_mod_check()
    @app_commands.describe(
        action="Filter by action type (create, edit, delete)",
        moderator="Filter by moderator (optional)"
    )
    @app_commands.command(name="logs", description="Show logs of event creation, edits, and deletion.")
    async def event_logs(
        self,
        interaction: discord.Interaction,
        action: Optional[str] = None,
        moderator: Optional[discord.User] = None,
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        with db_session() as session:
            logs = events_crud.get_event_logs(
                session=session,
                log_action=action,
                performed_by=str(moderator.id) if moderator else None
            )
    
            if not logs:
                await interaction.followup.send("❌ No logs found with those filters.")
                return
        
            pages = []
            for i in range(0, len(logs), LOGS_PER_PAGE):
                chunk = logs[i:i+LOGS_PER_PAGE]
                embed = discord.Embed(
                    title=f"📜 Event Logs ({i+1}-{i+len(chunk)}/{len(logs)})",
                    color=discord.Color.orange()
                )
                for log in chunk:
                    label = f"Event `{log.event_key}`" if log.event_key else "Deleted Event"
                    entry_str = format_log_entry(
                        log_action=log.log_action,
                        performed_by=log.performed_by,
                        performed_at=log.performed_at,
                        log_description=log.log_description,
                        label=label
                    )
                    embed.add_field(name="\n", value=entry_str, inline=False)
                pages.append(embed)
        
            await paginate_embeds(interaction, pages)


    # === SET EVENT STATUS ===
    @admin_or_mod_check()
    @app_commands.describe(
        shortcode="Shortcode of the event",
        event_status="New status: draft, visible, active, archived"
    )
    @app_commands.choices(
        event_status=[
            app_commands.Choice(name="Draft", value="draft"),
            app_commands.Choice(name="Visible", value="visible"),
            app_commands.Choice(name="Active", value="active"),
            app_commands.Choice(name="Archived", value="archived")
        ]
    )
    @app_commands.command(name="setstatus", description="Change the lifecycle status of an event.")
    async def set_event_status(
        self,
        interaction: discord.Interaction,
        shortcode: str,
        event_status: app_commands.Choice[str]
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        new_status = EventStatus(event_status.value)
        
        with db_session() as session:
            
            event = events_crud.get_event_by_key(
                session=session, 
                event_key=shortcode
            )
            if not event:                
                await interaction.followup.send(f"❌ Event `{shortcode}` not found.")
                return            

            old_status = event.event_status
            
            # Validation logic
            allowed_transitions = {
                EventStatus.draft: [EventStatus.visible],
                EventStatus.visible: [EventStatus.active, EventStatus.draft],
                EventStatus.active: [EventStatus.archived, EventStatus.visible, EventStatus.draft],
                EventStatus.archived: []
            }

            if new_status not in allowed_transitions[old_status]:
                await interaction.followup.send(
                    f"❌ Cannot move from {old_status.value} to {new_status.value}."
                )
                return
    
            if new_status == EventStatus.visible and not event.embed_message_discord_id:
                await interaction.followup.send("❌ You must define the embed message before making an event visible.")
                return

            status_update_data = {
                "event_status": new_status,
                "modified_by": str(interaction.user.id)
            }

            event = events_crud.set_event_status(
                session=session,
                event_key=shortcode,
                status_update_data=status_update_data
            )

            safe_event_name = event.event_name
            role_discord_id = event.role_discord_id

            # Announcement messages
            msg = None
            if old_status == EventStatus.draft and new_status == EventStatus.visible:
                msg = f"📢 The event **{safe_event_name}** is now visible to all members!"
            elif old_status == EventStatus.visible and new_status == EventStatus.active:
                msg = f"🎉 The event **{safe_event_name}** is now **active**!\nMembers can submit actions and browse the event rewards in the shop."
            elif old_status == EventStatus.active and new_status == EventStatus.archived:
    # Announcement messages
                msg = f"📢 **{safe_event_name}** is now **closed**. Thank you all for participating! 🎉\nLeaderboard and history remain accessible."
    
            if msg:
                await post_announcement_message(
                    interaction=interaction,
                    announcement_channel_id=EVENT_ANNOUNCEMENT_CHANNEL_ID,
                    msg=msg,
                    role_discord_id=role_discord_id
                )

        await interaction.followup.send(f"✅ Event `{safe_event_name} ({shortcode})` status changed to **{new_status.value}**.")


# === Setup Function ===
async def setup(bot):
    await bot.add_cog(AdminEventCommands(bot))