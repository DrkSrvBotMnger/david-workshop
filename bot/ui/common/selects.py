# bot/ui/common/selects.py
import discord
from typing import List, Callable, Awaitable, Optional, Any

AsyncOnSelect = Callable[[discord.Interaction, str], Awaitable[None]]

def build_select_options_from_vms(
    vms: List[Any],
    *,
    get_value=lambda vm: vm.value,
    get_label=lambda vm: vm.label,
    get_description=lambda vm: vm.description,
    limit: int = 25,
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
    """Reusable select view: provide options + async on_select handler."""
    def __init__(
        self,
        options: List[discord.SelectOption],
        on_select: AsyncOnSelect,
        *,
        placeholder: str = "Choose an option…",
        timeout: Optional[float] = 180,
    ):
        super().__init__(timeout=timeout)
        self.add_item(_GenericSelect(options, on_select, placeholder))