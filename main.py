import discord
from discord.ext import commands
import asyncio
import os

class MyBot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension("admin_commands")
        print("Admin commands loaded.")

# Bot setup
intents = discord.Intents.default()
bot = MyBot(command_prefix="!", intents=intents)

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
