import discord
from datetime import datetime
from discord import app_commands, Interaction, Embed
from discord.ext import commands
from typing import Optional
from bot.crud import events_crud, general_crud
from bot.config import EMBED_CHANNEL_ID, EVENT_ANNOUNCEMENT_CHANNEL_ID, EVENTS_PER_PAGE, LOGS_PER_PAGE
from bot.utils import admin_or_mod_check, safe_parse_date, confirm_action, paginate_embeds, format_discord_timestamp, format_log_entry
from db.database import db_session
from db.schema import EventLog

class AdminEventCommands(commands.GroupCog, name="admin_event"):
    """Admin commands for managing events."""
    def __init__(self, bot):
        self.bot = bot

    ## Event management commands
    # === CREATE EVENT ===
    @admin_or_mod_check()
    @app_commands.describe(
        shortcode="Unique shortcode (e.g. darklinaweek)",
        name="Full name of the event",
        description="Public-facing description",
        start_date="Start date (YYYY-MM-DD)",
        end_date="End date (YYYY-MM-DD) (optional)",
        coordinator="Optional mod managing the event, defaults to you",
        tags="Comma-separated tags (e.g. rp, halloween) (optional)",
        embed_channel="Channel where the display embed lives (optional)",
        embed_message_id="Message id of the embed to reuse (optional)",
        role_id = "Discord role id to tag during announcements (optional)",
        priority="Order to display in listings (higher = higher)",
        shop_section_id="Shop category ID tied to this event"
        )
    @app_commands.command(name="create", description="Create a new event.")
    async def create_event(
        self,
        interaction: discord.Interaction,
        shortcode: str,
        name: str,
        description: str,
        start_date: str,
        end_date: Optional[str] = None,
        coordinator: Optional[discord.Member] = None,
        tags: Optional[str] = None,
        embed_channel: Optional[discord.TextChannel] = None,
        embed_message_id: Optional[str] = None,
        role_id: Optional[str] = None,
        priority: int = 0,
        shop_section_id: Optional[str] = None
    ):
        """Creates an event. Event ID is auto-generated from shortcode + start month."""

        await interaction.response.defer(thinking=True, ephemeral=True)

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

        # Auto-generate event_id
        event_id = f"{shortcode.lower()}_{start_date_parsed[:7].replace('-', '_')}"

        # Handle coordinator
        if coordinator:
            coordinator_id = str(coordinator.id)
            coordinator_display = coordinator.mention
        else:
            coordinator_id = str(interaction.user.id)
            coordinator_display = interaction.user.mention

        # Handle tags and embed channel
        tag_str = tags.strip() if tags else None
        embed_channel_id = str(embed_channel.id) if embed_channel else EMBED_CHANNEL_ID
        
        if priority < 0:
            await interaction.followup.send("❌ Priority must be a non-negative integer.")
            return
        
        # Check for existing event_id then create event
        try:
            with db_session() as session:    
                existing_event = events_crud.get_event(session, event_id)
                if existing_event:
                    await interaction.followup.send(
                        f"❌ An event with ID `{event_id}` already exists. Choose a different shortcode or start date."
                    )
                    return

                event = events_crud.create_event(
                    session,
                    event_id=event_id,
                    name=name,
                    type="freeform",
                    description=description,
                    start_date=start_date_parsed,
                    end_date=end_date_parsed,
                    created_by=str(interaction.user.id),
                    coordinator_id=coordinator_id,
                    priority=priority,
                    shop_section_id=shop_section_id,
                    active=False,
                    visible=False,
                    tags=tag_str,
                    embed_channel_id=embed_channel_id,
                    embed_message_id=embed_message_id,
                    role_id=role_id
                )

                # Extract now while session is open
                safe_event_name = event.name

        except Exception as e:
            print(f"❌ DB failure: {e}")
            await interaction.followup.send("❌ An unexpected error occurred.")
            return

        msg = f"✅ Event `{safe_event_name}` created with ID `{event_id}`.\n👤 Coordinator: {coordinator_display}"
        if not coordinator:
            msg += " *(defaulted to you)*"

        await interaction.followup.send(content=msg)


    # === EDIT EVENT ===
    @admin_or_mod_check()
    @app_commands.describe(
        event_id="ID of the event to edit",
        name="New full name (optional)",
        description="New description (optional)",
        start_date="New start date (YYYY-MM-DD)",
        end_date="New end date (YYYY-MM-DD, use CLEAR to remove)",
        coordinator="New coordinator (optional)",
        tags="New comma-separated tags (use CLEAR to remove)",
        embed_channel="New channel for the display embed",
        embed_message_id="New embed message id to reuse (use CLEAR to remove)",
        role_id = "New discord role id to tag during announcements (use CLEAR to remove)",
        priority="Updated display priority (use CLEAR to remove)",
        shop_section_id="New shop category ID (use CLEAR to remove)",
        reason="Optional reason for editing (will be logged)"
    )
    @app_commands.command(name="edit", description="Edit an existing event's metadata.")
    async def edit_event(
        self,
        interaction: discord.Interaction,
        event_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        coordinator: Optional[discord.Member] = None,
        tags: Optional[str] = None,
        embed_channel: Optional[discord.TextChannel] = None,
        embed_message_id: Optional[str] = None,
        role_id: Optional[discord.Role] = None,
        priority: Optional[str] = None,
        shop_section_id: Optional[str] = None,
        reason: Optional[str] = None
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

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

        # Check for existing event_id then update event
        with db_session() as session:
            event = events_crud.get_event(session, event_id)
            if not event:
                await interaction.followup.send(f"❌ Event `{event_id}` not found.")
                return

            # Prevent editing active events							   
            if event.active:
                await interaction.followup.send("⚠️ This event is active and cannot be edited. Use a separate command to deactivate it first.")
                return

            updates = {}
            if name: 
                updates["name"] = name
            if description: 
                updates["description"] = description
            if start_date_parsed: 
                updates["start_date"] = start_date_parsed
            if end_date:
                updates["end_date"] = None if end_date.strip().upper() == "CLEAR" else end_date_parsed
            if coordinator: 
                updates["coordinator_id"] = str(coordinator.id)
            if tags:
                if tags.strip().upper() == "CLEAR":
                    updates["tags"] = None
                else:
                    updates["tags"] = ",".join(tag.strip() for tag in tags.split(","))            
            if embed_channel: 
                updates["embed_channel_id"] = str(embed_channel.id)
            if embed_message_id:
                if embed_message_id.strip().upper() == "CLEAR":
                    if event.visible:
                        await interaction.followup.send("❌ You cannot remove the embed message ID while the event is visible. Hide it first.")
                        return
                    updates["embed_message_id"] = None
                else:
                    updates["embed_message_id"] = embed_message_id.strip()
            if role_id:
                updates["role_id"] = None if role_id.strip().upper() == "CLEAR" else role_id.strip()
            if priority:
                if priority.strip().upper() == "CLEAR":
                    updates["priority"] = 0
                else:
                    try:
                        val = int(priority)
                        if val < 0:
                            raise ValueError
                        updates["priority"] = val
                    except ValueError:
                        await interaction.followup.send("❌ Priority must be a non-negative integer or CLEAR.")
                        return
            if shop_section_id:
                updates["shop_section_id"] = None if shop_section_id.strip().upper() == "CLEAR" else shop_section_id

            if not updates:
                await interaction.followup.send("❌ No valid fields provided to update.")
                return

            updated = events_crud.update_event(
                session,
                event_id=event_id,
                modified_by=str(interaction.user.id),
                modified_at=str(datetime.utcnow()),
                reason=reason,
                **updates
            )
            if not updated:
                await interaction.followup.send("❌ Event update failed unexpectedly.")
                return

            # Extract now while session is open								   
            safe_event_name = event.name

        await interaction.followup.send(
            f"✅ Event `{safe_event_name} ({event_id})` updated successfully." + (f"\n📝 Reason: {reason}" if reason else "")
        )


    # === DELETE EVENT ===
    @admin_or_mod_check()
    @app_commands.describe(
        event_id="ID of the event to delete",
        reason="Reason for deleting (will be logged)"
    )
    @app_commands.command(name="delete", description="Delete an event.")
    async def delete_event(
        self, 
        interaction: discord.Interaction, 
        event_id: str, 
        reason: str
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            event = events_crud.get_event(session, event_id)
            if not event:
                await interaction.edit_original_response(content=f"❌ Event `{event_id}` not found.")
                return

            if event.active or event.visible:
                await interaction.edit_original_response(content="⚠️ Cannot delete an event that is active or visible. Please deactivate/hide it first.")
                return
            
            # Extract now while session is open
            safe_event_name = event.name

        # Ask for confirmation
        confirmed = await confirm_action(interaction, f"event `{event_id}` ({safe_event_name})", reason)
        if not confirmed:
            await interaction.edit_original_response(content="❌ Deletion cancelled or timed out.", view=None)
            return

        with db_session() as session:
            success = events_crud.delete_event(
                session,
                event_id=event_id,
                deleted_by=str(interaction.user.id),
                reason=reason
            )
            if not success:
                await interaction.edit_original_response(content="❌ Event deletion failed unexpectedly.", view=None)
                return

        await interaction.edit_original_response(content=f"✅ Event `{safe_event_name}` deleted.", view=None)


    # === DISPLAY EVENT ===
    @admin_or_mod_check()
    @app_commands.describe(
        event_id="Id of the event to show"
    )
    @app_commands.command(name="display", description="Make an event visible to users.")
    async def display_event(
        self, 
        interaction: Interaction, 
        event_id: str
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            event = events_crud.get_event(session, event_id)
            if not event:
                await interaction.followup.send(f"❌ Event `{event_id}` not found.")
                return

            if event.visible:
                await interaction.followup.send("⚠️ This event is already visible.")
                return

            if not event.embed_message_id:
                await interaction.followup.send(
                    "❌ You must define the embed message before making an event visible."
                )
                return

            event.visible = True
            safe_event_name = event.name
            event_role_id = event.role_id
            
            # Track who modified the event
            event.modified_by = str(interaction.user.id)
            event.modified_at = str(datetime.utcnow())
            
            general_crud.log_change(
                session=session,
                log_model=EventLog,
                fk_field="event_id",
                fk_value=event.id,
                action="edit",
                performed_by=event.modified_by,
                description=f"Event {event.name} ({event.event_id}) made visible."
            )
        
        # Post announcement in announcement channel
        try:
            announcement_channel = interaction.guild.get_channel(EVENT_ANNOUNCEMENT_CHANNEL_ID)
            if announcement_channel:
                msg = f"📢 The event **{safe_event_name}** is now visible to all members!"
                # Add role ping if applicable
                if event_role_id:
                    msg = f"<@&{event_role_id}>\n{msg}"

                await announcement_channel.send(msg)
        except Exception as e:
            print(f"⚠️ Failed to post activation message in channel: {e}")


        await interaction.followup.send(f"✅ Event `{safe_event_name} ({event_id})` is now visible.")


    # === ACTIVATE EVENT ===
    @admin_or_mod_check()
    @app_commands.describe(
        event_id="ID of the event to activate (starts tracking and shows rewards)"
    )
    @app_commands.command(name="activate", description="Mark an event as active (and visible if needed).")
    async def activate_event(
        self, 
        interaction: discord.Interaction, 
        event_id: str
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            event = events_crud.get_event(session, event_id)
            if not event:
                await interaction.followup.send(f"❌ Event `{event_id}` not found.")
                return

            if event.active:
                await interaction.followup.send("⚠️ This event is already active.")
                return

            if not event.embed_message_id:
                await interaction.followup.send(
                    "❌ Cannot activate an event without an embed message ID. Use `/admin editevent` to define one first."
                )
                return

            event.active = True

            was_visible = event.visible
            if not event.visible:
                event.visible = True  # auto-enable visibility

            safe_event_name = event.name
            event_role_id = event.role_id

            # Track who modified the event
            event.modified_by = str(interaction.user.id)
            event.modified_at = str(datetime.utcnow())
            
            # Logging
            visibility_note = " (also made visible automatically)" if not was_visible else ""
            
            general_crud.log_change(
                session=session,
                log_model=EventLog,
                fk_field="event_id",
                fk_value=event.id,
                action="edit",
                performed_by=str(interaction.user.id),
                description=f"Event {event.name} ({event.event_id}) marked as active{visibility_note}."
            )
             
            # Post announcement in announcement channel
        try:
            announcement_channel = interaction.guild.get_channel(EVENT_ANNOUNCEMENT_CHANNEL_ID)
            if announcement_channel:
                msg = f"🎉 The event **{safe_event_name}** is now **active**!\nMembers can submit actions and browse the event rewards in the shop."
                # Add role ping if applicable
                if event_role_id:
                    msg = f"<@&{event_role_id}>\n{msg}"
                await announcement_channel.send(msg)
        except Exception as e:
            print(f"⚠️ Failed to post activation message in channel: {e}")

        await interaction.followup.send(f"✅ Event `{safe_event_name} ({event_id})` marked as active{visibility_note}.")


    # === DEACTIVATE EVENT ===
    @admin_or_mod_check()
    @app_commands.describe(
        event_id="ID of the event to deactivate (ends tracking and disables rewards)"
    )
    @app_commands.command(name="deactivate", description="Mark an event as inactive (tracking ends, still visible).")
    async def deactivate_event(
        self, 
        interaction: discord.Interaction, 
        event_id: str
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)
    
        with db_session() as session:
            event = events_crud.get_event(session, event_id)
            if not event:
                await interaction.followup.send(f"❌ Event `{event_id}` not found.")
                return
    
            if not event.active:
                await interaction.followup.send("⚠️ This event is already inactive.")
                return
    
            event.active = False
            safe_event_name = event.name
            event_role_id = event.role_id

            # Track who modified the event
            event.modified_by = str(interaction.user.id)
            event.modified_at = str(datetime.utcnow())
    
            general_crud.log_change(
                session=session,
                log_model=EventLog,
                fk_field="event_id",
                fk_value=event.id,
                action="edit",
                performed_by=str(interaction.user.id),
                description=f"Event {event.name} ({event.event_id}) marked as inactive."
            )
    
        # Post announcement
        try:
            announcement_channel = interaction.guild.get_channel(EVENT_ANNOUNCEMENT_CHANNEL_ID)
            if announcement_channel:
                msg = f"📢 **{safe_event_name}** is now **closed**. Thank you all for participating! 🎉\nLeaderboard and history remain accessible."
                # Add role ping if applicable
                if event_role_id:
                    msg = f"<@&{event_role_id}>\n{msg}"
                await announcement_channel.send(msg)
        except Exception as e:
            print(f"⚠️ Failed to post deactivation message: {e}")
    
        await interaction.followup.send(f"✅ Event `{safe_event_name} ({event_id})` marked as inactive.")
    
    
    # === HIDE EVENT ===
    @admin_or_mod_check()
    @app_commands.describe(event_id="ID of the event to hide (removes from public views)")
    @app_commands.command(name="hide", description="Hide an event from users (must not be active).")
    async def hide_event(self, interaction: discord.Interaction, event_id: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
    
        with db_session() as session:
            event = events_crud.get_event(session, event_id)
            if not event:
                await interaction.followup.send(f"❌ Event `{event_id}` not found.")
                return
    
            if event.active:
                await interaction.followup.send("❌ You must deactivate the event before hiding it.")
                return
    
            if not event.visible:
                await interaction.followup.send("⚠️ This event is already hidden.")
                return
    
            event.visible = False
            safe_event_name = event.name

            # Track who modified the event
            event.modified_by = str(interaction.user.id)
            event.modified_at = str(datetime.utcnow())
    
            general_crud.log_change(
                session=session,
                log_model=EventLog,
                fk_field="event_id",
                fk_value=event.id,
                action="edit",
                performed_by=str(interaction.user.id),
                description=f"Event {event.name} ({event.event_id}) marked as hidden."
            )
    
        await interaction.followup.send(f"✅ Event `{safe_event_name} ({event_id})` is now hidden from users.")


    # === LIST EVENTS ===
    @admin_or_mod_check()
    @app_commands.describe(
        tag="Filter by tag (optional)",
        active="Only show active events",
        visible="Only show visible events",
        mod_name="Only show events created or edited by this mod"
    )
    @app_commands.command(name="list", description="List all events with filters")
    async def list_events(
        self,
        interaction: Interaction,
        tag: str = None,
        active: bool = None,
        visible: bool = None,
        mod_name: discord.User = None
    ):
        
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        with db_session() as session:
            events = events_crud.get_all_events(session)
            
            if tag:
                events = [e for e in events if e.tags and tag.strip().lower() in [t.strip().lower() for t in e.tags.split(",")]]

            if active is not None:
                events = [e for e in events if e.active == active]
            if visible is not None:
                events = [e for e in events if e.visible == visible]
            if mod_name:
                uid = str(mod_name.id)
                events = [e for e in events if e.created_by == uid or e.modified_by == uid]

            # Sort newest to oldest
            events.sort(key=lambda e: e.modified_at or e.created_at, reverse=True)
            
            pages = []
            for i in range(0, len(events), EVENTS_PER_PAGE):
                chunk = events[i:i+EVENTS_PER_PAGE]
                embed = Embed(title=f"🗂️ Events List ({i+1}-{i+len(chunk)}/{len(events)})")
                for e in chunk:
                    updated_by = f"<@{e.modified_by}>" if e.modified_by else f"<@{e.created_by}>"
                    formatted_time = format_discord_timestamp(e.modified_at or e.created_at)

                    lines = [
                        f"**ID:** `{e.event_id}` | **Name:** {e.name}",
                        f"👤 Last updated by: {updated_by}",
                        f":timer: On: {formatted_time}",
                        f"🔎 Visible: {'✅' if e.visible else '❌'} | :tada:  Active: {'✅' if e.active else '❌'} | 📎 Embed: {'✅' if e.embed_message_id else '❌'} | 🎭 Role: {'✅' if e.role_id else '❌'}",
                    ]
                    embed.add_field(name="\n", value="\n".join(lines), inline=False)
                pages.append(embed)
        await paginate_embeds(interaction, pages)


    # === SHOW EVENT METADATA ===
    @admin_or_mod_check()
    @app_commands.describe(
        event_id="ID of the event to show in detail"
    )
    @app_commands.command(name="show", description="Display full metadata of a specific event.")
    async def show_event(self, interaction: Interaction, event_id: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
    
        with db_session() as session:
            event = events_crud.get_event(session, event_id)
            if not event:
                await interaction.followup.send(f"❌ Event `{event_id}` not found.", ephemeral=True)
                return

            end_date = event.end_date or "*Ongoing*"
            visible_status = "✅" if event.visible else "❌"
            active_status = "✅" if event.active else "❌"
            role_status = "✅" if event.role_id else "❌"
            embed_status = "✅" if event.embed_message_id else "❌"
            tag_display = event.tags if event.tags else "*None*"
            description = event.description if event.description else "*No description*"    
            shop_section = event.shop_section_id if event.shop_section_id else "*None*"
            priority = str(event.priority)
            created_edited = f"By: <@{event.created_by}> at {format_discord_timestamp(event.created_at)}"
            if event.modified_by :
                created_edited = f"{created_edited}\nLast: <@{event.modified_by}> at {format_discord_timestamp(event.modified_at)}"
            
            embed = Embed(title=f"📋 Event Details: {event.name}", color=0x7289DA)
            embed.add_field(name="🆔 ID", value=event.event_id, inline=False)  
            embed.add_field(name="📅 Dates", value=f"Start: {event.start_date}\nEnd: {end_date}", inline=True)
            embed.add_field(name="🔎 Visible", value=visible_status, inline=True)
            embed.add_field(name="🎉 Active", value=active_status, inline=True)

            embed.add_field(name="👤 Coordinator", value=f"<@{event.coordinator_id}>", inline=True)          
            embed.add_field(name="🎭 Role", value=embed_status, inline=True)
            embed.add_field(name="🧵 Embed?", value=role_status, inline=True)

            embed.add_field(name="🛒 Shop Section", value=shop_section, inline=True)
            embed.add_field(name="⭐ Priority", value=priority, inline=True)
            embed.add_field(name=" ", value="", inline=True)

            embed.add_field(name="🏷️ Tags", value=tag_display, inline=False)
            embed.add_field(name="✏️ Description", value=description, inline=False)
            if event.embed_message_id:
                jump_link = f"https://discord.com/channels/{interaction.guild.id}/{event.embed_channel_id}/{event.embed_message_id}"
                embed.add_field(name="🔗 Embed Link", value=f"[Jump to Embed]({jump_link})", inline=False)
            
            embed.add_field(name="👩‍💻 Created / Edited By", value=created_edited, inline=False)
    
            await interaction.followup.send(embed=embed, ephemeral=True)


    # === EVENT LOGS ===
    @admin_or_mod_check()
    @app_commands.describe(
        action="Filter by action type (create, edit, delete)",
        moderator="Filter by moderator (optional)"
    )
    @app_commands.command(name="logs", description="Show logs of event creation, edits, and deletion.")
    async def eventlog(
        self,
        interaction: discord.Interaction,
        action: Optional[str] = None,
        moderator: Optional[discord.User] = None,
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)
    
        with db_session() as session:
            logs = events_crud.get_all_event_logs(session)
    
            if action:
                logs = [(log, eid) for log, eid in logs if log.action == action.lower()]
            if moderator:
                logs = [(log, eid) for log, eid in logs if log.performed_by == str(moderator.id)]
    
            # Sort most recent first
            logs.sort(key=lambda l: l[0].timestamp, reverse=True)
    
            if not logs:
                await interaction.followup.send("❌ No logs found with those filters.", ephemeral=True)
                return
    
            embeds = []
            for i in range(0, len(logs), LOGS_PER_PAGE):
                chunk = logs[i:i+LOGS_PER_PAGE]
                embed = discord.Embed(
                    title=f"📜 Event Logs ({i+1}-{i+len(chunk)}/{len(logs)})",
                    color=discord.Color.orange()
                )
                for log, event_id_str in chunk:
                    label = f"Event `{event_id_str}`" if event_id_str else "Deleted Event"
                    entry_str = format_log_entry(
                        action=log.action,
                        performed_by=log.performed_by,
                        timestamp=log.timestamp,
                        description=log.description,
                        label=label
                    )
                    embed.add_field(name="\n", value=entry_str, inline=False)
                embeds.append(embed)
    
        await paginate_embeds(interaction, embeds)


# === Setup Function ===
async def setup(bot):
    await bot.add_cog(AdminEventCommands(bot))