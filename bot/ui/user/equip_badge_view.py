# bot/ui/user/equip_badge_view.py
import discord
from discord import Interaction, SelectOption
from discord.ui import View, Select, Button
from typing import Optional, Callable, Awaitable, List

from db.database import db_session
from bot.crud.inventory_crud import set_badges_equipped
from bot.config.constants import MAX_BADGES

class EquipBadgeView(View):
    """
    Equip badges view. Receives a list of options to display.
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
        self.add_item(EquipBadgeSelect(user_db_id, options, author_id, on_refresh_profile))
        self.add_item(UnequipAll(user_db_id, author_id, on_refresh_profile))

    async def interaction_check(self, interaction: Interaction) -> bool:
        # Author lock
        select: EquipBadgeSelect | None = next((c for c in self.children if isinstance(c, EquipBadgeSelect)), None)
        author_id = getattr(select, "author_id", None)
        if author_id and interaction.user.id != author_id:
            await interaction.response.send_message("This menu isn’t yours.", ephemeral=True)
            return False
        return True


class EquipBadgeSelect(Select):
    """
    Select menu for equipping badges.
    """
    def __init__(
        self,
        user_db_id: int,
        options: List[SelectOption],
        author_id: int,
        on_refresh_profile: Optional[Callable[[], Awaitable[None]]],
    ):
        max_vals = min(MAX_BADGES, len(options)) or 1
        super().__init__(placeholder=f"Select up to {MAX_BADGES} badges",
                         min_values=0, max_values=max_vals, options=options)
        self.user_db_id = user_db_id
        self.author_id = author_id
        self._on_refresh_profile = on_refresh_profile

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This menu isn’t yours.", ephemeral=True)
            return

        selected_keys = list(self.values)[:MAX_BADGES]

        # 1) DB
        try:
            with db_session() as session:
                set_badges_equipped(session, self.user_db_id, selected_keys)
        except Exception as e:
            print("❌ equip badges error:", e)
            await interaction.response.edit_message(content="❌ Failed to update badges.", view=None)
            return

        # 2) edit THIS ephemeral and close it
        await interaction.response.edit_message(
            content=f"✅ Badges updated. Equipped **{len(selected_keys)}**.",
            view=None
        )

        # 3) refresh public
        if self._on_refresh_profile:
            try:
                await self._on_refresh_profile()
            except Exception as e:
                print("⚠️ refresh profile failed:", e)


class UnequipAll(Button):
    """
    Button to unequip all badges.
    """
    def __init__(
        self,
        user_db_id: int,
        author_id: int,
        on_refresh_profile: Optional[Callable[[], Awaitable[None]]],
    ):
        super().__init__(label="Unequip all", style=discord.ButtonStyle.danger)
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
                set_badges_equipped(session, self.user_db_id, [])
        except Exception as e:
            print("❌ unequip badges error:", e)
            await interaction.response.edit_message(content="❌ Failed to unequip badges.", view=None)
            return

        # 2) edit THIS ephemeral and close it
        await interaction.response.edit_message(content="🧹 All badges unequipped.", view=None)

        # 3) refresh public
        if self._on_refresh_profile:
            try:
                await self._on_refresh_profile()
            except Exception as e:
                print("⚠️ refresh profile failed:", e)