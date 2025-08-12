# bot/ui/user/events_views.py
import discord
from typing import Optional, Awaitable, Callable, List
from bot.ui.common.selects import GenericSelectView, build_select_options_from_vms
from bot.presentation.events_presentation import EventOptionVM
from bot.config import TICKET_CHANNEL_ID

AsyncOnSelect = Callable[[discord.Interaction, str], Awaitable[None]]
AsyncBack = Callable[[discord.Interaction], Awaitable[None]]

def make_user_event_select_view(vms: List[EventOptionVM], on_select: AsyncOnSelect) -> discord.ui.View:
    options = build_select_options_from_vms(vms)
    return GenericSelectView(options, on_select, placeholder="Choose an event…")

class UserEventButtons(discord.ui.View):
    def __init__(self, guild_id: int, back_to_list: Optional[AsyncBack] = None):
        super().__init__(timeout=180)
        self._back_to_list = back_to_list

        # Contact Mods
        ticket_url = f"https://discord.com/channels/{guild_id}/{TICKET_CHANNEL_ID}"
        self.add_item(discord.ui.Button(label="📩 Contact Mods", style=discord.ButtonStyle.link, url=ticket_url))

        # Enable/disable Back depending on callback presence
        try:
            self.go_back.disabled = back_to_list is None
        except Exception:
            pass

    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.secondary)
    async def go_back(self, interaction: discord.Interaction, _btn: discord.ui.Button):
        if not self._back_to_list:
            await interaction.response.defer()
            return
        await self._back_to_list(interaction)  # delegate to cog