import discord
from discord.ext import commands
import asyncio
import os

from discord import app_commands

class MyBot(commands.Bot):
    async def setup_hook(self):
        try:
            await self.load_extension("bot.commands.admin")
            print("✅ Admin commands loaded.")
        except Exception as e:
            print(f"❌ Failed to load admin commands: {e}")

# Bot setup
intents = discord.Intents.default()
intents.members = True
intents.guilds = True  # Optional, but recommended
intents.message_content = True  # If needed elsewhere

bot = MyBot(command_prefix="!", intents=intents)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        try:
            await interaction.response.send_message(
                "❌ You don’t have permission to use this command.",
                ephemeral=True
            )
        except discord.InteractionResponded:
            await interaction.followup.send(
                "❌ You don’t have permission to use this command.",
                ephemeral=True
            )

        
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# Asynchronous main function
async def main():
    TOKEN = os.getenv("DISCORD_TOKEN")
    await bot.start(TOKEN)

# Run bot
if __name__ == "__main__":
    asyncio.run(main())
