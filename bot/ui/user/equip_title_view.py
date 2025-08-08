import discord
from discord import Interaction
from discord.ui import View, Select, Button
from db.database import db_session
from db.schema import Inventory, Reward


class EquipTitleSelect(Select):
    def __init__(self, user_db_id: int, options):
        super().__init__(
            placeholder="Select a title",
            min_values=0,               # <<— allow “none” (unequip all)
            max_values=1,
            options=options
        )
        self.user_db_id = user_db_id

    async def callback(self, interaction: Interaction):
        selected = set(self.values)
        with db_session() as session:
            items = (
                session.query(Inventory).join(Reward)
                .filter(Inventory.user_id == self.user_db_id, Reward.reward_type == "title")
                .all()
            )
            for it in items:
                it.is_equipped = it.reward.reward_key in selected
            session.flush()
        await interaction.response.edit_message(content="✅ Title updated.", view=None)


class UnequipTitle(Button):
    def __init__(self, user_db_id: int):
        super().__init__(label="Unequip title", style=discord.ButtonStyle.danger)
        self.user_db_id = user_db_id

    async def callback(self, interaction: Interaction):
        with db_session() as session:
            items = (
                session.query(Inventory).join(Reward)
                .filter(Inventory.user_id == self.user_db_id, Reward.reward_type == "title")
                .all()
            )
            for it in items:
                it.is_equipped = False
            session.flush()
        await interaction.response.edit_message(content="🧹 Title unequipped.", view=None)


class EquipTitleView(View):
    def __init__(self, user_db_id: int, options):
        super().__init__(timeout=60)
        self.add_item(EquipTitleSelect(user_db_id, options))
        self.add_item(UnequipTitle(user_db_id))