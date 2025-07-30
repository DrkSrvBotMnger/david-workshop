# bot/commands/admin/actions_admin.py
import discord
from discord import app_commands
from discord.ext import commands
from bot.commands.admin.admin_root import admin_group


class AdminActionCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @admin_group.command(name="createaction", description="Create a new action.")
    async def create_action(self, interaction: discord.Interaction, name: str):
        await interaction.response.send_message(f"Action `{name}` created.")

async def setup(bot):
    await bot.add_cog(AdminActionCommands(bot))
