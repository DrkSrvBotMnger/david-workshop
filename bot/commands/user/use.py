from discord import app_commands, Interaction
from discord.ext import commands
import discord

from db.database import db_session
from db.schema import Inventory, Reward
from bot.crud import users_crud

# --- View / Select ---

class UsePresetSelect(discord.ui.Select):
    def __init__(self, options_data: list[tuple[str, str, str]]):
        """
        options_data: list of (label, value, description)
          - value MUST encode "channel_id:message_id" to avoid re-querying
        """
        
        options = []
        for label, value, desc in options_data[:25]:  # Discord hard limit
            options.append(discord.SelectOption(label=label[:100], value=value, description=(desc or "")[:100]))
        super().__init__(placeholder="Choose a preset to use…", min_values=1, max_values=1, options=options, custom_id="use_preset_select")

    async def callback(self, interaction: Interaction):
        # value is "channel_id:message_id"
        payload = self.values[0]
        try:
            ch_id_str, msg_id_str = payload.split(":", 1)
            channel = await interaction.client.fetch_channel(int(ch_id_str))
            original_msg = await channel.fetch_message(int(msg_id_str))
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to fetch preset message: {e}", ephemeral=True)
            return
            
        print(f"original_msg.content: {original_msg.content}")
        # Repost in the channel where user ran /use
        await interaction.channel.send(content=original_msg.content, embeds=original_msg.embeds, files=[await a.to_file() for a in original_msg.attachments])
        await interaction.response.send_message("✅ Preset used!", ephemeral=True)


class UsePresetView(discord.ui.View):
    def __init__(self, options_data: list[tuple[str, str, str]], *, timeout: float = 120):
        super().__init__(timeout=timeout)
        self.add_item(UsePresetSelect(options_data))


# --- Cog / Command ---

class UserInventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="use", description="Use one of your preset rewards")
    async def use_preset(self, interaction: Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            # Ensure user exists
            user = users_crud.get_or_create_user(session, interaction.user)

            # Fetch only usable presets the user owns
            rows = (
                session.query(Inventory, Reward)
                .join(Reward, Inventory.reward_id == Reward.id)
                .filter(
                    Inventory.user_id == user.id,
                    Reward.reward_type == "preset",
                    Reward.use_channel_discord_id.isnot(None),
                    Reward.use_message_discord_id.isnot(None),
                )
                .all()
            )

            if not rows:
                await interaction.followup.send("You don’t have any usable presets right now.", ephemeral=True)
                return

            # Build select options IN the session, but pass the data out so the view needs no DB.
            options_data = []
            for inv, r in rows:
                label = f"{(r.emoji or '').strip()} {r.reward_name}".strip()
                # Pack channel+message in value: "channel_id:message_id"
                value = f"{int(r.use_channel_discord_id)}:{int(r.use_message_discord_id)}"
                desc = r.reward_key  # short hint; could include event key if you want
                options_data.append((label, value, desc))

        view = UsePresetView(options_data)
        await interaction.followup.send("Pick a preset to use:", view=view, ephemeral=True)


# === COG SETUP ===
async def setup(bot):
    await bot.add_cog(UserInventory(bot))