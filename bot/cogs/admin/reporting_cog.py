# bot/cogs/admin/reporting_cog.py
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
import traceback

from bot.ui.admin.reporting_views import AdminReportsHomeView
from bot.utils.permissions import admin_or_mod_check


class ReportingCog(commands.Cog, name="Admin Reporting"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @admin_or_mod_check()
    @app_commands.command(name="admin_reports", description="Admin: open reporting UI.")
    async def admin_reports(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            view = AdminReportsHomeView(author_id=interaction.user.id)
            await interaction.followup.send("📊 **Admin Reporting** — pick an event and a report type.", view=view, ephemeral=True)
        except Exception:
            traceback.print_exc()
            await interaction.followup.send("⚠️ Couldn’t open the reporting UI. Check logs for details.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ReportingCog(bot))