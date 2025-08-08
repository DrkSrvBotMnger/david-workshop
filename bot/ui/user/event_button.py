import discord
from bot.config import TICKET_CHANNEL_ID


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