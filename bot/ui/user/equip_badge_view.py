import discord
from discord import Interaction
from discord.ui import View, Select, Button
from db.database import db_session
from db.schema import Inventory, Reward


class EquipBadgeSelect(Select):
    def __init__(self, user_db_id: int, options):
        max_vals = min(8, len(options)) or 1
        super().__init__(
            placeholder="Select up to 12 badges",
            min_values=0,               # <<— allow “none” (unequip all)
            max_values=max_vals,
            options=options
        )
        self.user_db_id = user_db_id

    async def callback(self, interaction: Interaction):
        selected = set(self.values)
        with db_session() as session:
            items = (
                session.query(Inventory).join(Reward)
                .filter(Inventory.user_id == self.user_db_id, Reward.reward_type == "badge")
                .all()
            )
            for it in items:
                it.is_equipped = it.reward.reward_key in selected
            session.commit()
        await interaction.response.edit_message(content="✅ Badges updated.", view=None)


class UnequipAll(Button):
    def __init__(self, user_db_id: int):
        super().__init__(label="Unequip all", style=discord.ButtonStyle.danger)
        self.user_db_id = user_db_id

    async def callback(self, interaction: Interaction):
        with db_session() as session:
            items = (
                session.query(Inventory).join(Reward)
                .filter(Inventory.user_id == self.user_db_id, Reward.reward_type == "badge")
                .all()
            )
            for it in items:
                it.is_equipped = False
            session.flush()
        await interaction.response.edit_message(content="🧹 All badges unequipped.", view=None)


class EquipBadgeView(View):
    def __init__(self, user_db_id: int, options):
        super().__init__(timeout=60)
        self.add_item(EquipBadgeSelect(user_db_id, options))
        self.add_item(UnequipAll(user_db_id))