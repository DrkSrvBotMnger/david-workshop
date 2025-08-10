import discord
from bot.config import TICKET_CHANNEL_ID
from db.database import db_session
from bot.crud import events_crud
from discord import app_commands, File, Interaction, Embed, User as DiscordUser, SelectOption
from db.schema import Event

class EventSelect(discord.ui.Select):
    def __init__(self, options_data: list[dict]):
        opts = [
            discord.SelectOption(
                label=o["label"][:100],
                value=o["value"],
                description=(o.get("description") or "")[:100]
            )
            for o in options_data[:25]  # Discord hard limit
        ]
        super().__init__(placeholder="Choose an event…", min_values=1, max_values=1, options=opts)
        self._payload = {o["value"]: o for o in options_data}

    async def callback(self, interaction: discord.Interaction):
        event_key = self.values[0]
    
        # Pull only the scalar fields we need, then close the session.
        # 1) DB read (as you had)
        with db_session() as session:
            row = (
                session.query(
                    Event.embed_channel_discord_id,
                    Event.embed_message_discord_id,
                    Event.event_name,
                    Event.event_key
                )
                .filter(Event.event_key == event_key)
                .first()
            )
            if not row:
                await interaction.response.send_message("❌ Event not found anymore.", ephemeral=True)
                return

            channel_id, message_id, event_name, ev_key = row

            if not (channel_id and message_id):
                await interaction.response.send_message("⚠️ This event has no stored message.", ephemeral=True)
                return    

        # 2) Fetch the original message
        try:
            channel = interaction.guild.get_channel(int(channel_id)) or \
                      await interaction.client.fetch_channel(int(channel_id))
            message = await channel.fetch_message(int(message_id))
        except Exception as e:
            print(f"⚠️ Failed to fetch event message: {e}")
            await interaction.response.send_message("❌ Could not retrieve the event message.", ephemeral=True)
            return

        # 3) Prepare files and view BEFORE responding
        files = [await a.to_file() for a in message.attachments[:10] if a]

        # Build buttons and set real ticket link
        view = EventButtons(ev_key, event_name, guild_id=interaction.guild.id)

        content = f"**{event_name}**\n{message.content.strip()}" if (message.content and message.content.strip()) else f"**{event_name}**"

        # 4) Respond ONCE
        try:
            kwargs = {
                "content": content,
                "embeds": message.embeds[:10],
                "view": view,
                "ephemeral": True,
            }
            if files:
                kwargs["files"] = files
            await interaction.response.send_message(**kwargs)
            print("✅ Sent event message copy.")
            
        except Exception as e:
            # Fallback without files if Discord rejects attachments/embeds
            print(f"⚠️ Sending event copy failed: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(content=content, embeds=message.embeds[:10], view=view, ephemeral=True)
            else:
                await interaction.followup.send(content=content, embeds=message.embeds[:10], view=view, ephemeral=True)


class EventSelectView(discord.ui.View):
    def __init__(self, options_data: list[dict], *, timeout=180):
        super().__init__(timeout=timeout)
        self.add_item(EventSelect(options_data))


class EventButtons(discord.ui.View):
    def __init__(self, event_key: str, event_name: str, guild_id: int):
        super().__init__(timeout=None)
        self.event_key = event_key
        self.event_name = event_name

        ticket_url = f"https://discord.com/channels/{guild_id}/{TICKET_CHANNEL_ID}"
        self.add_item(discord.ui.Button(
            label="📩 Contact Mods",
            style=discord.ButtonStyle.link,
            url=ticket_url
        ))

    #@discord.ui.button(label="✅ Join Event", style=discord.ButtonStyle.success)
    #async def join_event(self, interaction: discord.Interaction, button: discord.ui.Button):
    #    await interaction.response.send_message(
    #        f"✅ You have joined the event `{self.event_name} ({self.event_key})`!\n"
    #        "(Feature coming soon: auto log your participation.)",
    #        ephemeral=True
    #    )