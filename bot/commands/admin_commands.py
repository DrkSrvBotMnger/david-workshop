import discord
from discord import app_commands
from discord.ext import commands
from utils import is_moderator
from db.database import db_session
import crud

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Admin command group root
    admin_group = app_commands.Group(
        name="admin",
        description="Moderator-only commands."
    )

    ## Event management commands
    
    # === CREATE EVENT ===
    @admin_group.command(name="createevent", description="Create a new event.")
    async def create_event(self, interaction: discord.Interaction,
                           shortcode: str,
                           name: str,
                           description: str,
                           start_date: str,  # Format: YYYY-MM-DD
                           end_date: str,    # Format: YYYY-MM-DD
                           coordinator: discord.Member,
                           active: bool = False,
                           visible: bool = False,
                           priority: int = 0,
                           shop_section_id: str = None,
                           embed_color: str = "#7289DA"):  # HEX input
        """Creates an event. Event ID is auto-generated from shortcode + start month."""

      #  if not is_moderator(interaction.user):
      #      await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
      #      return

        # Auto-generate event_id
        event_id = f"{shortcode.lower()}_{start_date[:7].replace('-', '_')}"
        coordinator_id = str(coordinator.id)

        # Parse HEX color to integer
        try:
            embed_color_int = int(embed_color.lstrip("#"), 16)
        except ValueError:
            await interaction.response.send_message("❌ Invalid HEX color format. Use something like #7289DA.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        # Check for existing event_id
        with db_session() as session:    
            existing_event = crud.get_event(session, event_id)
            if existing_event:
                await interaction.response.send_message(
                    f"❌ An event with ID `{event_id}` already exists. Choose a different shortcode or start date.",
                    ephemeral=True
                )
                return

            event = crud.create_event(
                session,
                event_id=event_id,
                name=name,
                type_="freeform",
                description=description,
                start_date=start_date,
                end_date=end_date,
                created_by=str(interaction.user.id),
                coordinator_id=coordinator_id,
                priority=priority,
                shop_section_id=shop_section_id,
                embed_color=embed_color_int,
                metadata_json=None,  # Metadata locked for now
                active=active,
                visible=visible
            )

        await interaction.followup.send(
            f"✅ Event `{event.name}` created with ID `{event_id}`.",
            ephemeral=True
        )


    # === EDIT EVENT ===
    @admin_group.command(name="editevent", description="Edit an existing event.")
    async def edit_event(self, interaction: discord.Interaction,
                         event_id: str,
                         field: str,
                         value: str):
        if not is_moderator(str(interaction.user.id)):
            await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
            return

        with db_session() as session:
            event = crud.update_event(
                session,
                event_id=event_id,
                modified_by=str(interaction.user.id),
                **{field: value}
            )
            if not event:
                await interaction.response.send_message(f"❌ Event `{event_id}` not found.", ephemeral=True)
                return

        await interaction.response.send_message(f"✅ Event `{event_id}` updated: `{field}` set to `{value}`.", ephemeral=True)


    # === DELETE EVENT ===
    @admin_group.command(name="deleteevent", description="Delete an event.")
    async def delete_event(self, interaction: discord.Interaction, event_id: str):
        if not is_moderator(str(interaction.user.id)):
            await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
            return

        with db_session() as session:
            success = crud.delete_event(
                session,
                event_id=event_id,
                deleted_by=str(interaction.user.id)
            )
            if not success:
                await interaction.response.send_message(f"❌ Event `{event_id}` not found.", ephemeral=True)
                return

        await interaction.response.send_message(f"✅ Event `{event_id}` deleted.", ephemeral=True)


    # === EVENT LOG ===
    @admin_group.command(name="eventlog", description="View event logs.")
    async def event_log(self, interaction: discord.Interaction, event_id: str = None):
        if not is_moderator(str(interaction.user.id)):
            await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
            return

        with db_session() as session:
            logs = crud.get_event_logs(session, event_id=event_id)

        if not logs:
            await interaction.response.send_message("No event logs found.", ephemeral=True)
            return

        log_lines = [f"{log.timestamp} – {log.action} by {log.performed_by}" for log in logs[:10]]
        log_message = "\n".join(log_lines)

        await interaction.response.send_message(f"📜 **Event Logs:**\n{log_message}", ephemeral=True)


# === Setup Function ===
async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
