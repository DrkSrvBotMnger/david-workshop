# bot/cogs/user/profile_cog.py
import discord
from discord import app_commands, Interaction
from typing import Optional
from discord.ext import commands

from bot.config.constants import MAX_BADGES
from bot.utils.discord_helpers import resolve_display_name
from db.database import db_session

# UI
from bot.ui.user.profile_views import ProfileView
from bot.ui.user.inventory_views import InventoryView
from bot.ui.user.equip_badge_view import EquipBadgeView
from bot.ui.user.equip_title_view import EquipTitleView

# Presentation
from bot.presentation.profile_presentation import fetch_profile_vm, build_profile_file_and_name
from bot.services.equip_service import get_title_select_options, get_badge_select_options

# Services
from bot.services.users_service import get_or_create_user_dto
from bot.services.inventory_service import get_user_publishables_for_preview

# CRUD
from bot.crud.inventory_crud import fetch_user_inventory_ordered

class ProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------- internal callbacks ----------------

    async def _open_inventory(self, inter: Interaction, target: discord.Member | discord.User):
        with db_session() as s:
            user = get_or_create_user_dto(s, target)
            items = fetch_user_inventory_ordered(s, user.id)
            display_name = resolve_display_name(user)
            publishables = get_user_publishables_for_preview(s, user.id)

        async def _view_profile(cb_inter: discord.Interaction):
            vm = fetch_profile_vm(target)
            file, _ = await build_profile_file_and_name(vm)
            is_owner = (target.id == cb_inter.user.id)
            view = ProfileView(
                on_open_inventory=lambda i: self._open_inventory(i, target),
                on_equip_title=self._open_equip_title,
                on_equip_badges=self._open_equip_badges,
                author_id=cb_inter.user.id,    
                enable_equip=is_owner,         
            )
            await cb_inter.response.edit_message(attachments=[file], view=view, embed=None)

        inv_view = InventoryView(
            viewer=target,
            items=items,
            on_view_profile=_view_profile,    
            display_name=display_name,
            author_id=inter.user.id,   
            publishables=publishables,        
        )
        await inter.response.edit_message(embed=inv_view.build_embed(), view=inv_view, attachments=[])

    async def _open_equip_title(self, inter: discord.Interaction):
        
        origin_msg = inter.message
        panel_author_id = inter.user.id
        target = inter.user  # owner

        async def refresh_profile():
            vm = fetch_profile_vm(target)
            file, _ = await build_profile_file_and_name(vm)
            view = ProfileView(
                on_open_inventory=lambda i: self._open_inventory(i, target),
                on_equip_title=self._open_equip_title,
                on_equip_badges=self._open_equip_badges,
                author_id=panel_author_id,
                enable_equip=True,
            )
            await origin_msg.edit(attachments=[file], embed=None, view=view)

        user_db_id, options = get_title_select_options(inter.user)
        view = EquipTitleView(
            user_db_id, 
            options, 
            author_id=panel_author_id, 
            on_refresh_profile=refresh_profile
        )
        await inter.response.send_message("🎖️ Choose the title you want to equip:", view=view, ephemeral=True)

    async def _open_equip_badges(self, inter: discord.Interaction):
        
        panel_author_id = inter.user.id
        origin_msg = inter.message
        target = inter.user  # owner

        async def refresh_profile():
            vm = fetch_profile_vm(target)
            file, _ = await build_profile_file_and_name(vm)
            view = ProfileView(
                on_open_inventory=lambda i: self._open_inventory(i, target),
                on_equip_title=self._open_equip_title,
                on_equip_badges=self._open_equip_badges,
                author_id=panel_author_id,
                enable_equip=True,
            )
            await origin_msg.edit(attachments=[file], embed=None, view=view)

        user_db_id, options = get_badge_select_options(inter.user)
        view = EquipBadgeView(
            user_db_id, 
            options, 
            author_id=panel_author_id, 
            on_refresh_profile=refresh_profile
        )
        await inter.response.send_message(f"🎖️ Choose the badges you want to equip ({MAX_BADGES}):", view=view, ephemeral=True)
 
    # ---------------- slash commands ----------------
    # === PROFILE COMMAND ===
    @app_commands.command(name="profile", description="Show your current points and rewards.")
    async def profile(self, interaction: Interaction, member: Optional[discord.Member] = None):
        await interaction.response.defer(ephemeral=False)
        target = member or interaction.user
        
        vm = fetch_profile_vm(target)
        file, _ = await build_profile_file_and_name(vm)
    
        is_owner = (target.id == interaction.user.id)
        view = ProfileView(
            on_open_inventory=lambda i: self._open_inventory(i, target),
            on_equip_title=self._open_equip_title,
            on_equip_badges=self._open_equip_badges,
            author_id=interaction.user.id,    
            enable_equip=is_owner,           
        )
        await interaction.followup.send(file=file, view=view, ephemeral=False)

    # === INVENTORY COMMAND ===
    @app_commands.command(name="inventory", description="Show your (or another member's) inventory")
    @app_commands.describe(member="Whose inventory to view (optional)")
    async def inventory(self, interaction: Interaction, member: discord.Member | None = None):
        target = member or interaction.user

        with db_session() as s:
            user = get_or_create_user_dto(s, target)                 # DB user DTO
            publishables = get_user_publishables_for_preview(s, user.id)  # DB id (FIX)
            items = fetch_user_inventory_ordered(s, user.id)
            display_name = resolve_display_name(user)

        async def _back(cb_inter: Interaction):
            vm = fetch_profile_vm(target)
            file, _ = await build_profile_file_and_name(vm)
            is_owner = (target.id == cb_inter.user.id)
            view = ProfileView(
                on_open_inventory=lambda i: self._open_inventory(i, target),
                on_equip_title=self._open_equip_title,
                on_equip_badges=self._open_equip_badges,
                author_id=cb_inter.user.id,
                enable_equip=is_owner,
            )
            await cb_inter.response.edit_message(attachments=[file], view=view, embed=None)

        view = InventoryView(
            viewer=target,
            items=items,
            on_view_profile=_back,
            display_name=display_name,
            author_id=interaction.user.id,
            publishables=publishables, 
        )

        await interaction.response.send_message(
            embed=view.build_embed(),
            view=view,
            ephemeral=True
        )

    # === EQUIP BADGE COMMAND ===
    @app_commands.command(name="equip_badge", description=f"Select up to {MAX_BADGES} badges to display on your profile.")
    async def equip_badge(self, interaction: Interaction):
        # mirror button behavior: defer ephemeral, then use followup
        try:
            await interaction.response.defer(ephemeral=True, thinking=False)
        except discord.InteractionResponded:
            pass

        user_db_id, options = get_badge_select_options(interaction.user)
        if not options:
            await interaction.followup.send("ℹ️ You don't own any badges yet.", ephemeral=True)
            return

        view = EquipBadgeView(
            user_db_id=user_db_id, 
            options=options,
            author_id=interaction.user.id
        )
        await interaction.followup.send(f"🎖️ Choose the badges you want to equip (max. {MAX_BADGES}):", view=view, ephemeral=True)

    # === EQUIP TITLE COMMAND ===
    @app_commands.command(name="equip_title", description="Select a title to display on your profile.")
    async def equip_title(self, interaction: Interaction):
        try:
            await interaction.response.defer(ephemeral=True, thinking=False)
        except discord.InteractionResponded:
            pass

        user_db_id, options = get_title_select_options(interaction.user)
        if not options:
            await interaction.followup.send("ℹ️ You don't own any title yet.", ephemeral=True)
            return

        view = EquipTitleView(
            user_db_id=user_db_id, 
            options=options,
            author_id=interaction.user.id
        )
        await interaction.followup.send("🎖️ Choose the title you want to equip:", view=view, ephemeral=True)

# === COG SETUP ===
async def setup(bot):
    await bot.add_cog(ProfileCog(bot))