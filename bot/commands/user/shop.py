from discord import app_commands, Interaction, SelectOption, Embed
from discord.ext import commands
from discord.ui import View, Button, Select
from db.database import db_session
from bot.crud import users_crud
from bot.crud.shop_crud import get_inshop_catalog_grouped
from bot.crud.purchase_crud import fetch_reward_event, apply_purchase, PurchaseError
from bot.ui.user.shop_dashboard_view import ShopPager


class ShopCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # === SHOP COMMAND ===
    @app_commands.command(name="shop", description="Browse the event shop.")
    async def shop(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        with db_session() as session:
            pages = get_inshop_catalog_grouped(session)
            user = users_crud.get_or_create_user(session, interaction.user)
            user_points = user.points
        if not pages:
            await interaction.followup.send("No active event has items in the shop right now.")
            return
        try:
            view = ShopPager(pages, user_points)
            await interaction.followup.send(embed=view._make_embed(), view=view, ephemeral=True)
        except Exception as e:
            print(f"❌ Error in shop command: {e}")
            await interaction.followup.send("❌ Something went wrong loading the shop.", ephemeral=True)
            return


# === COG SETUP ===
async def setup(bot):
    await bot.add_cog(ShopCommands(bot))