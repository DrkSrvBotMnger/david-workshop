import discord
from typing import Awaitable, Callable

class ProfileView(discord.ui.View):
    """UI-only. Button delegates to a cog callback."""
    def __init__(self, on_open_inventory: Callable[[discord.Interaction], Awaitable[None]]):
        super().__init__(timeout=120)
        self._on_open_inventory = on_open_inventory

    @discord.ui.button(label="Open Inventory", style=discord.ButtonStyle.primary, custom_id="profile:open_inventory")
    async def open_inventory(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self._on_open_inventory(interaction)