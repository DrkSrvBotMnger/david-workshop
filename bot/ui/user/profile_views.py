import discord
from typing import Awaitable, Callable

class ProfileView(discord.ui.View):
    def __init__(
        self,
        on_open_inventory: Callable[[discord.Interaction], Awaitable[None]],
        on_equip_title: Callable[[discord.Interaction], Awaitable[None]],
        on_equip_badges: Callable[[discord.Interaction], Awaitable[None]],
        *,
        author_id: int,          
        enable_equip: bool,      
    ):
        super().__init__(timeout=120)
        self._on_open_inventory = on_open_inventory
        self._on_equip_title = on_equip_title
        self._on_equip_badges = on_equip_badges
        self.author_id = author_id
        self.enable_equip = enable_equip

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This profile panel isn’t yours.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Open Inventory", style=discord.ButtonStyle.primary, custom_id="profile:open_inventory")
    async def open_inventory(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self._on_open_inventory(interaction)

    @discord.ui.button(label="Equip Title", style=discord.ButtonStyle.secondary, custom_id="profile:equip_title")
    async def equip_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.enable_equip:
            await interaction.response.send_message("You can’t change someone else’s title.", ephemeral=True)
            return
        await self._on_equip_title(interaction)

    @discord.ui.button(label="Equip Badges", style=discord.ButtonStyle.secondary, custom_id="profile:equip_badges")
    async def equip_badges(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.enable_equip:
            await interaction.response.send_message("You can’t change someone else’s badges.", ephemeral=True)
            return
        await self._on_equip_badges(interaction)