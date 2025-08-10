# bot/ui/user/equip_title_view.py
import discord
from discord import Interaction, SelectOption
from discord.ui import View, Select, Button
from typing import Optional, Callable, Awaitable, List

from db.database import db_session
from bot.crud.inventory_crud import set_titles_equipped

# on_refresh_profile: a no-arg coroutine you pass from the cog that edits the public profile message.
# It must NOT use interaction.response/followup.

class EquipTitleView(View):
    """
    Equip title view. Receives a list of options to display.
    """
    def __init__(
        self,
        user_db_id: int,
        options: List[SelectOption],
        *,
        author_id: int,
        on_refresh_profile: Optional[Callable[[], Awaitable[None]]] = None,  # << changed signature
    ):
        super().__init__(timeout=60)
        self.author_id = author_id
        self._on_refresh_profile = on_refresh_profile
        self.add_item(EquipTitleSelect(user_db_id, options, author_id, self._on_refresh_profile))
        self.add_item(UnequipTitle(user_db_id, author_id, self._on_refresh_profile))

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This menu isn’t yours.", ephemeral=True)
            return False
        return True

class EquipTitleSelect(Select):
    """
    Select menu for equipping a title.
    """
    def __init__(
        self,
        user_db_id: int,
        options: List[SelectOption],
        author_id: int,
        on_refresh_profile: Optional[Callable[[], Awaitable[None]]],
    ):
        super().__init__(placeholder="Select a title (or none to unequip)",
                         min_values=0, max_values=1, options=options)
        self.user_db_id = user_db_id
        self.author_id = author_id
        self._on_refresh_profile = on_refresh_profile

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This menu isn’t yours.", ephemeral=True)
            return

        selected_key: Optional[str] = self.values[0] if self.values else None

        # 1) update DB (quick; no defer)
        try:
            with db_session() as session:
                set_titles_equipped(session, self.user_db_id, selected_key)
        except Exception as e:
            print("❌ equip title error:", e)
            await interaction.response.edit_message(content="❌ Failed to update title.", view=None)
            return

        # 2) edit THIS ephemeral, close controls
        if selected_key:
            label = next((opt.label for opt in self.options if opt.value == selected_key), selected_key)
            content = f"✅ Title updated: **{label}**."
        else:
            content = "🧹 Title unequipped."
        await interaction.response.edit_message(content=content, view=None)

        # 3) refresh public profile (no replies here)
        if self._on_refresh_profile:
            try:
                await self._on_refresh_profile()
            except Exception as e:
                print("⚠️ refresh profile failed:", e)


class UnequipTitle(Button):
    """
    Button to unequip the title.
    """
    def __init__(
        self,
        user_db_id: int,
        author_id: int,
        on_refresh_profile: Optional[Callable[[], Awaitable[None]]],
    ):
        super().__init__(label="Unequip title", style=discord.ButtonStyle.danger)
        self.user_db_id = user_db_id
        self.author_id = author_id
        self._on_refresh_profile = on_refresh_profile

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This menu isn’t yours.", ephemeral=True)
            return

        # 1) DB
        try:
            with db_session() as session:
                set_titles_equipped(session, self.user_db_id, None)
        except Exception as e:
            print("❌ unequip title error:", e)
            await interaction.response.edit_message(content="❌ Failed to unequip title.", view=None)
            return

        # 2) edit THIS ephemeral and close it
        await interaction.response.edit_message(content="🧹 Title unequipped.", view=None)

        # 3) refresh public
        if self._on_refresh_profile:
            try:
                await self._on_refresh_profile()
            except Exception as e:
                print("⚠️ refresh profile failed:", e)
