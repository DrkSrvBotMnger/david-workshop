# main.py
import os
import sys
import asyncio
import logging
import discord
from discord import app_commands
from discord.ext import commands

# ---------------- Single-instance guard (robust) ----------------
import fcntl

LOCK_PATH = "/tmp/dw_bot.lock"
_lock_fd = os.open(LOCK_PATH, os.O_CREAT | os.O_RDWR, 0o644)
try:
    fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    os.ftruncate(_lock_fd, 0)
    os.write(_lock_fd, str(os.getpid()).encode())
except BlockingIOError:
    print("Another instance seems to be running; exiting.")
    sys.exit(1)

# ---------------- Optional: quick preflight to avoid 429 loops ----------------
import aiohttp

async def discord_preflight() -> bool:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://discord.com/api/v10") as r:
                if r.status == 429:
                    ra = r.headers.get("retry-after")
                    logging.error(f"Cloudflare rate-limited host IP (429). retry-after={ra}")
                    return False
    except Exception as e:
        logging.warning(f"Preflight check failed: {e}")
    return True

# ---------------- Bot definition ----------------
class MyBot(commands.Bot):
    async def setup_hook(self):
        # Load all cogs first
        admin_cogs = [
            "bot.commands.admin.events_admin",
            "bot.commands.admin.actions_admin",
            "bot.commands.admin.rewards_admin",
            #"bot.commands.admin.event_links_wizard",
            "bot.commands.admin.event_links_admin",
            "bot.commands.admin.trigger_rewards_cog",
            "bot.commands.admin.mod_economy",
            "bot.cogs.admin.prompts_cog",
            "bot.cogs.admin.event_triggers_cog"
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
intents.guilds = True
intents.message_content = True  # if truly needed

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

# ---------------- Async main with clean shutdown ----------------
async def main():
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("DISCORD_TOKEN is not set.")
        return

    # Optional preflight to avoid hammering when IP is blocked
    if not await discord_preflight():
        return

    try:
        await bot.start(token)
    finally:
        # Always close the bot and release the lock
        try:
            await bot.close()
        except Exception:
            pass
        try:
            fcntl.flock(_lock_fd, fcntl.LOCK_UN)
            os.close(_lock_fd)
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())
