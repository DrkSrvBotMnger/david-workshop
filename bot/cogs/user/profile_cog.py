import discord
from discord import app_commands, File, Interaction, SelectOption
from typing import Optional
from discord.ext import commands

from db.database import db_session
from db.schema import EventStatus, Inventory, Reward, User, Event

# UI
from bot.ui.user.profile_views import ProfileView
from bot.ui.user.inventory_views import InventoryView
from bot.ui.user.event_button import EventSelectView
from bot.ui.user.equip_badge_view import EquipBadgeView
from bot.ui.user.equip_title_view import EquipTitleView

# Services (helpers moved out of the cog)
from bot.services.profile_service import fetch_profile_vm, build_profile_file_and_name
from bot.services.inventory_service import fetch_inventory_for_member


class ProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------- internal callbacks ----------------

    async def _open_inventory(self, inter: Interaction, target: discord.Member | discord.User):
        """
        Component callback: replace the current message with the user's inventory.
        View remains DB-free; we fetch everything here (via service).
        """
        user_row, items, display_name = fetch_inventory_for_member(target)

        async def _back_to_profile(cb_inter: Interaction):
            # Re-render profile on the SAME message
            vm = fetch_profile_vm(target)
            file, _ = await build_profile_file_and_name(vm)
            view = ProfileView(on_open_inventory=lambda i: self._open_inventory(i, target))
            await cb_inter.response.edit_message(attachments=[file], view=view, embed=None)

        inv_view = InventoryView(
            viewer=target,
            items=items,
            on_back_to_profile=_back_to_profile,
            display_name=display_name,  # pass the resolved name
        )
        await inter.response.edit_message(embed=inv_view.build_embed(), view=inv_view, attachments=[])

    # ---------------- slash commands ----------------

    @app_commands.command(name="profile", description="Show your current points and rewards.")
    async def profile(self, interaction: Interaction, member: Optional[discord.Member] = None):
        """
        Sends the profile card image + an 'Open Inventory' button.
        """
        await interaction.response.defer(ephemeral=False)
        target = member or interaction.user
        try:
            vm = fetch_profile_vm(target)
            file, _display_name = await build_profile_file_and_name(vm)
            view = ProfileView(on_open_inventory=lambda i: self._open_inventory(i, target))
            await interaction.followup.send(file=file, view=view, ephemeral=False)
        except Exception as e:
            print("❌ Error generating profile card:", e)
            await interaction.followup.send("❌ Something went wrong generating your profile card.", ephemeral=True)

    @app_commands.command(name="inventory", description="Show your (or another member's) inventory")
    @app_commands.describe(member="Whose inventory to view (optional)")
    async def inventory(self, interaction: Interaction, member: discord.Member | None = None):
        """
        Standalone inventory command. Also offers a Back-to-Profile button.
        """
        target = member or interaction.user
        user_row, items, display_name = fetch_inventory_for_member(target)

        async def _back(cb_inter: Interaction):
            vm = fetch_profile_vm(target)
            file, _ = await build_profile_file_and_name(vm)
            view = ProfileView(on_open_inventory=lambda i: self._open_inventory(i, target))
            await cb_inter.response.edit_message(attachments=[file], view=view, embed=None)

        view = InventoryView(
            viewer=target,
            items=items,
            on_back_to_profile=_back,
            display_name=display_name,  # ensure the view never guesses names
        )
        await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)



    
    # === VIEW EVENT COMMAND ===
    @app_commands.command(name="event", description="Browse current events.")
    async def view_event(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            # Only visible/active events that have a saved original message
            rows = (
                session.query(Event)
                .filter(Event.event_status.in_([EventStatus.visible, EventStatus.active]))
                .filter(Event.embed_channel_discord_id.isnot(None))
                .filter(Event.embed_message_discord_id.isnot(None))
                .order_by(Event.priority.desc(), Event.start_date.asc(), Event.event_name.asc())
                .all()
            )

            if not rows:
                await interaction.followup.send("There are no events to show right now.", ephemeral=True)
                return

            options: list[dict] = []
            for ev in rows[:25]:  # Discord limit
                options.append({
                    "label": ev.event_name,
                    "value": ev.event_key,                 # internal id for callback
                    "description": ev.event_type or "Event"
                })

        view = EventSelectView(options)
        await interaction.followup.send("Select an event to view:", view=view, ephemeral=True)


    # === EQUIP BADGE COMMAND ===
    @app_commands.command(name="equip_badge", description="Select up to 12 badges to display on your profile.")
    async def equip_badge(self, interaction: Interaction):
        
        with db_session() as session:

            user = session.query(User).filter_by(user_discord_id=str(interaction.user.id)).first()

            rows = (
                session.query(
                    Reward.reward_key, Reward.reward_name, Reward.emoji, Inventory.is_equipped
                )
                .join(Inventory, Inventory.reward_id == Reward.id)
                .filter(Inventory.user_id == user.id, Reward.reward_type == "badge")
                .all()
            )
            if not rows:
                await interaction.response.send_message("ℹ️ You don't own any badges yet.", ephemeral=True)
                return

            options = [
                SelectOption(
                    label=(name or key),
                    value=key,
                    emoji=str(emoji),
                    default=equipped,           # <<— preselect already equipped
                )
                for key, name, emoji, equipped in rows
            ]

            user_db_id = user.id
        
        view = EquipBadgeView(user_db_id=user_db_id, options=options)
        await interaction.response.send_message("🎖️ Choose the badges you want to equip (max. 12):", view=view, ephemeral=True)


    # === EQUIP TITLE COMMAND ===
    @app_commands.command(name="equip_title", description="Select a title to display on your profile.")
    async def equip_title(self, interaction: Interaction):
    
        with db_session() as session:
    
            user = session.query(User).filter_by(user_discord_id=str(interaction.user.id)).first()
    
            rows = (
                session.query(
                    Reward.reward_key, Reward.reward_name, Inventory.is_equipped
                )
                .join(Inventory, Inventory.reward_id == Reward.id)
                .filter(Inventory.user_id == user.id, Reward.reward_type == "title")
                .all()
            )
            if not rows:
                await interaction.response.send_message("ℹ️ You don't own any title yet.", ephemeral=True)
                return
    
            options = [
                SelectOption(
                    label=(name or key),
                    value=key,
                    default=equipped,           # <<— preselect already equipped
                )
                for key, name, equipped in rows
            ]
    
            user_db_id = user.id
    
        view = EquipTitleView(user_db_id=user_db_id, options=options)
        await interaction.response.send_message("🎖️ Choose the title you want to equip:", view=view, ephemeral=True)


# === COG SETUP ===
async def setup(bot):
    await bot.add_cog(ProfileCog(bot))