# bot/cogs/admin/prompts_cog.py
from __future__ import annotations
import datetime as dt
import discord
from discord import app_commands
from discord.ext import commands

from bot.services.prompts_service import (
    upsert_event_prompts_bulk,
    list_event_prompts,
)
from bot.ui.admin.prompts_views import BulkPromptsModal


from bot.services.events_service import get_event_dto_by_key

class AdminPromptsCog(commands.Cog, name="Admin Prompts"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="admin_prompts_bulk_load", description="Bulk load prompts for an event (paste up to 31 lines).")
    @app_commands.describe(
        event_key="Event key (e.g., drkwk2508)",
        group="Prompt group (e.g., sfw, nsfw). Leave empty for none."
    )
    async def admin_prompts_bulk_load(
        self,
        interaction: discord.Interaction,
        event_key: str,
        group: str | None = None,
    ):
        ev = get_event_dto_by_key(event_key)
        if not ev:
            await interaction.response.send_message(f"❌ Event `{event_key}` not found.", ephemeral=True)
            return

        modal = BulkPromptsModal(ev.id, group, author_tag=str(interaction.user))
        # Show modal as the initial response (don't defer first)
        await interaction.response.send_modal(modal)

        # Wait for submit/cancel
        await modal.wait()
        if modal.result is None:
            # on_submit defers; if user closed modal, we still need to respond
            await interaction.followup.send("❌ Cancelled or timed out.", ephemeral=True)
            return

        labels = modal.result
        if not labels:
            await interaction.followup.send("⚠️ No prompts provided.", ephemeral=True)
            return

        now = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
        rows = upsert_event_prompts_bulk(
            event_id=ev.id,
            group=group,
            labels_in_order=labels,
            created_by=str(interaction.user),
            created_at=now,
        )

        codes = ", ".join(r.code for r in rows)
        suffix = f" (group: **{group}**)" if group else ""
        await interaction.followup.send(
            f"✅ Loaded **{len(rows)}** prompts for **{ev.event_key}**{suffix}.\n`{codes}`",
            ephemeral=True,
        )

    @app_commands.command(name="admin_prompts_list", description="List prompts for an event.")
    @app_commands.describe(
        event_key="Event key",
        group="Filter by group (optional)",
        active_only="Only active prompts?"
    )
    async def admin_prompts_list(
        self,
        interaction: discord.Interaction,
        event_key: str,
        group: str | None = None,
        active_only: bool = True,
    ):
        await interaction.response.defer(ephemeral=True)
        ev = get_event_dto_by_key(event_key)
        if not ev:
            await interaction.followup.send(f"❌ Event `{event_key}` not found.", ephemeral=True)
            return

        rows = list_event_prompts(event_id=ev.id, group=group, active_only=active_only)
        if not rows:
            await interaction.followup.send("No prompts found.", ephemeral=True)
            return

        lines = [f"`{r.code}` — {r.label}" + (f"  (#{r.day_index})" if r.day_index else "") for r in rows]
        msg = f"**Prompts for {ev.event_key}**" + (f" (group: **{group}**)" if group else "") + "\n" + "\n".join(lines[:50])
        await interaction.followup.send(msg, ephemeral=True)


    


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminPromptsCog(bot))