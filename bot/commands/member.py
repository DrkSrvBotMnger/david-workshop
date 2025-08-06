import discord
from discord import app_commands
from discord.ext import commands
from bot.crud import events_crud
from db.database import db_session
from db.schema import EventStatus
from bot.config import TICKET_CHANNEL_ID


# === EVENT BUTTONS VIEW ===
class EventButtons(discord.ui.View):
    def __init__(self, event_key: str, event_name: str):
        super().__init__(timeout=None)
        self.event_key = event_key
        self.event_name = event_name
        self.set_ticket_link()

    def set_ticket_link(self):
        """Adds a link button to the ticket/mod-mail channel."""
        ticket_url = f"https://discord.com/channels/{{guild_id}}/{TICKET_CHANNEL_ID}"

        # Instead of using a callback, we use a Discord link button
        contact_button = discord.ui.Button(
            label="📩 Contact Mods",
            style=discord.ButtonStyle.link,
            url=ticket_url
        )
        self.add_item(contact_button)

    @discord.ui.button(label="✅ Join Event", style=discord.ButtonStyle.success)
    async def join_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        # MVP: simple confirmation
        await interaction.response.send_message(
            f"✅ You have joined the event `{self.event_name} ({self.event_key})`!\n"
            "(Feature coming soon: auto log your participation.)",
            ephemeral=True
        )


# === MEMBER COMMANDS COG ===
class MemberCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    
    @app_commands.describe(shortcode="Shortcode of the event to view")
    @app_commands.command(name="event", description="View details for a visible event.")
    async def view_event(
        self,
        interaction: discord.Interaction,
        shortcode: str
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            event = events_crud.get_event_by_key(session, shortcode)
            if not event:
                await interaction.followup.send(f"❌ Event `{shortcode}` not found.", ephemeral=True)
                return

            if event.event_status == EventStatus.draft:
                await interaction.followup.send(f"⚠️ Event `{shortcode}` is not currently visible.", ephemeral=True)
                return

            if not event.embed_message_discord_id:
                await interaction.followup.send(
                    f"❌ Event `{shortcode}` is visible but no embed message is set.",
                    ephemeral=True
                )
                return

            try:
                channel = interaction.guild.get_channel(int(event.embed_channel_discord_id))
                if not channel:
                    raise ValueError("Channel not found")

                message = await channel.fetch_message(int(event.embed_message_discord_id))
                if not message.embeds:
                    raise ValueError("No embeds in stored message")

                # Build buttons with correct guild-specific ticket link
                view = EventButtons(event.event_key, event.event_name)
                for child in view.children:
                    if isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.link:
                        child.url = f"https://discord.com/channels/{interaction.guild.id}/{TICKET_CHANNEL_ID}"

                # Send all embeds + buttons (ephemeral for spam control)
                await interaction.followup.send(
                    embeds=message.embeds,
                    view=view
                )

            except Exception as e:
                print(f"⚠️ Failed to fetch event embed for {shortcode}: {e}")
                await interaction.followup.send(
                    f"❌ Could not retrieve the embed for `{shortcode}`. Please contact a moderator.",
                    ephemeral=True
                )


async def setup(bot):
    await bot.add_cog(MemberCommands(bot))
