import asyncio
import discord
import os
from discord import app_commands
from discord.ext import commands

class MyBot(commands.Bot):
    async def setup_hook(self):
    # Load all cogs first
        admin_cogs = [
            "bot.commands.admin.events_admin",
            "bot.commands.admin.actions_admin",
            "bot.commands.admin.rewards_admin",
            "bot.commands.admin.event_links_admin",
            "bot.commands.admin.mod_economy"
        ]
        for cog in admin_cogs:
            try:
                await self.load_extension(cog)
                print(f"✅ Loaded {cog}")
            except Exception as e:
                print(f"❌ Failed to load {cog}: {e}")

        user_cogs = [
            "bot.commands.user.shop",
            "bot.cogs.user.profile_cog",
            "bot.cogs.user.event_cog",
            "bot.commands.user.use",
            "bot.commands.user.report_action",
        ]    
        for cog in user_cogs:
            try:
                await self.load_extension(cog)
                print(f"✅ Loaded {cog}")
            except Exception as e:
                print(f"❌ Failed to load {cog}: {e}")

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
        for cmd in bot.tree.walk_commands():
            print(cmd.qualified_name)
    except Exception as e:
        print(f"Error syncing commands: {e}")

# Asynchronous main function
async def main():
    TOKEN = os.getenv("DISCORD_TOKEN")
    await bot.start(TOKEN)

# Run bot
if __name__ == "__main__":
    asyncio.run(main())
