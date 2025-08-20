# bot/ui/common/selects.py
import discord
from typing import List, Callable, Awaitable, Any

AsyncOnSelect = Callable[[discord.Interaction, str], Awaitable[None]]

def build_select_options_from_vms(
    vms: List[Any],
    *,
    get_value=lambda vm: vm.value,
    get_label=lambda vm: vm.label,
    get_description=lambda vm: vm.description,
    limit: int = None,
) -> List[discord.SelectOption]:
    """Turn value/label/description VMs into Discord options (truncates to 100 chars)."""
    opts: List[discord.SelectOption] = []
    for vm in vms[:limit]:  # Discord cap
        opts.append(discord.SelectOption(
            value=str(get_value(vm)),
            label=str(get_label(vm))[:100],
            description=(str(get_description(vm))[:100] if get_description(vm) else None),
        ))
    return opts

class _GenericSelect(discord.ui.Select):
    def __init__(self, options: List[discord.SelectOption], on_select: AsyncOnSelect, placeholder: str):
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)
        self._on_select = on_select

    async def callback(self, interaction: discord.Interaction):
        await self._on_select(interaction, self.values[0])

class GenericSelectView(discord.ui.View):
    def __init__(
        self,
        options: list[discord.SelectOption],
        on_select: AsyncOnSelect,
        placeholder: str = "Choose an option…",
        per_page: int = 25,
        timeout: float = 180,
    ):
        super().__init__(timeout=timeout)
        self.all_options = options
        self.on_select = on_select
        self.placeholder = placeholder
        self.per_page = per_page
        self.page = 0

        # Initialize buttons
        self.prev_button = self.PreviousPageButton()
        self.next_button = self.NextPageButton()

        self._refresh_select()

    def _refresh_select(self):
        start = self.page * self.per_page
        end = start + self.per_page
        sliced = self.all_options[start:end]
        select = _GenericSelect(sliced, self.on_select, self.placeholder)

        self.clear_items()
        self.add_item(select)

        if len(self.all_options) > self.per_page:
            self.add_item(self.prev_button)
            self.add_item(self.next_button)

    class PreviousPageButton(discord.ui.Button):
        def __init__(self):
            super().__init__(style=discord.ButtonStyle.secondary, emoji="⏮", row=1)

        async def callback(self, interaction: discord.Interaction):
            view: GenericSelectView = self.view
            view.page = max(view.page - 1, 0)
            view._refresh_select()
            await interaction.response.edit_message(view=view)

    class NextPageButton(discord.ui.Button):
        def __init__(self):
            super().__init__(style=discord.ButtonStyle.secondary, emoji="⏭", row=1)

        async def callback(self, interaction: discord.Interaction):
            view: GenericSelectView = self.view
            max_page = (len(view.all_options) - 1) // view.per_page
            view.page = min(view.page + 1, max_page)
            view._refresh_select()
            await interaction.response.edit_message(view=view)