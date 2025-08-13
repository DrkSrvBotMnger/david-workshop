# bot/ui/user/prompts_views.py
from __future__ import annotations
import math
import discord
from bot.domain.dto import EventPromptDTO

PAGE_SIZE = 25  # Discord limit

def _chunk(items: list[EventPromptDTO], size: int) -> list[list[EventPromptDTO]]:
    return [items[i:i+size] for i in range(0, len(items), size)]

class PromptPageSelect(discord.ui.Select):
    def __init__(self, prompts: list[EventPromptDTO], view_ref: "PromptPickerView"):
        self.view_ref = view_ref
        options = []
        for p in prompts:
            label = f"{p.code} — {p.label}"
            # value must be str
            options.append(discord.SelectOption(label=label[:100], value=str(p.id)))
        super().__init__(
            placeholder="Select prompt(s) for this page…",
            min_values=0,
            max_values=min(len(options), PAGE_SIZE),
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        # Merge this page's current selections into the global set.
        picked = set(int(v) for v in self.values)
        # Remove any previously-selected IDs from this page before adding new ones
        page_ids = {int(opt.value) for opt in self.options}
        self.view_ref.selected_ids.difference_update(page_ids)
        self.view_ref.selected_ids.update(picked)
        await self.view_ref.refresh(interaction)


class PromptPickerView(discord.ui.View):
    def __init__(self, prompts: list[EventPromptDTO], *, owner_id: int, timeout: float | None = 180):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.all_prompts: list[EventPromptDTO] = list(prompts)
        self.pages: list[list[EventPromptDTO]] = _chunk(self.all_prompts, PAGE_SIZE)
        self.page_index: int = 0
        self.selected_ids: set[int] = set()
        self.confirmed: bool = False

        if not self.pages:
            self.pages = [[]]

        self.page_select: PromptPageSelect | None = None
        self._rebuild_components()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user and interaction.user.id == self.owner_id

    async def refresh(self, interaction: discord.Interaction):
        self._rebuild_components()
        footer = self._footer()
        content = f"Select prompts (page {self.page_index+1}/{len(self.pages)})\n{footer}"
        try:
            await interaction.response.edit_message(content=content, view=self)
        except Exception:
            await interaction.edit_original_response(content=content, view=self)

    def _rebuild_components(self):
        self.clear_items()
        # Page select
        current = self.pages[self.page_index]
        self.page_select = PromptPageSelect(current, self)
        self.add_item(self.page_select)
        # Nav + confirm
        self.add_item(self.PrevButton())
        self.add_item(self.NextButton(total_pages=len(self.pages)))
        self.add_item(self.ConfirmButton())

    def _footer(self) -> str:
        count = len(self.selected_ids)
        if count == 0:
            return "No prompts selected yet."
        # Show preview of first few codes
        id_to_code = {p.id: p.code for p in self.all_prompts}
        preview = ", ".join(id_to_code[i] for i in list(self.selected_ids)[:8])
        more = "" if count <= 8 else f" …(+{count-8} more)"
        return f"Selected: {count} → {preview}{more}"

    class PrevButton(discord.ui.Button):
        def __init__(self):
            super().__init__(style=discord.ButtonStyle.secondary, label="◀ Prev")

        async def callback(self, interaction: discord.Interaction):
            v: PromptPickerView = self.view  # type: ignore
            v.page_index = (v.page_index - 1) % len(v.pages)
            await v.refresh(interaction)

    class NextButton(discord.ui.Button):
        def __init__(self, total_pages: int):
            super().__init__(style=discord.ButtonStyle.secondary, label="Next ▶")
            self.total_pages = total_pages

        async def callback(self, interaction: discord.Interaction):
            v: PromptPickerView = self.view  # type: ignore
            v.page_index = (v.page_index + 1) % len(v.pages)
            await v.refresh(interaction)

    class ConfirmButton(discord.ui.Button):
        def __init__(self):
            super().__init__(style=discord.ButtonStyle.success, label="✅ Confirm")

        async def callback(self, interaction: discord.Interaction):
            v: PromptPickerView = self.view  # type: ignore
            v.confirmed = True
            try:
                await interaction.response.defer(ephemeral=True)
            except Exception:
                pass
            v.stop()