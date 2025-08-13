# bot/ui/admin/prompts_views.py
from __future__ import annotations
import discord

class BulkPromptsModal(discord.ui.Modal):
    def __init__(self, event_id: int, group: str | None, *, author_tag: str):
        super().__init__(title="Bulk load prompts (1 per line, max 31)")
        self.event_id = event_id
        self.group = group
        self.author_tag = author_tag

        self.lines = discord.ui.TextInput(
            label="Prompts",
            style=discord.TextStyle.long,
            placeholder="One prompt per line…",
            required=True,
            max_length=4000,  # generous
        )
        self.add_item(self.lines)

        self.result: list[str] | None = None

    async def on_submit(self, interaction: discord.Interaction):
        # Normalize lines (strip empties), clamp to 31
        raw = self.lines.value.splitlines()
        labels = [ln.strip() for ln in raw if ln.strip()]
        labels = labels[:31]
        self.result = labels
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass
        self.stop()