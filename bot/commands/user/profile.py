import discord
from discord import app_commands, File, Interaction, Embed, User as DiscordUser, SelectOption
from typing import Optional, List, Union
from discord.ext import commands
from bot.crud import events_crud, users_crud
from db.database import db_session
from db.schema import EventStatus, Inventory, Reward, User, Event
from bot.config import TICKET_CHANNEL_ID
from bot.utils.profile_card import generate_profile_card  # path depends on your structure
from bot.utils.badge_loader import extract_badge_icons
from bot.utils.time_parse_paginate import now_iso
from bot.ui.user.event_button import EventButtons, EventSelectView
from bot.ui.user.equip_badge_view import EquipBadgeView
from bot.ui.user.equip_title_view import EquipTitleView
import aiohttp
import io
from PIL import Image, ImageDraw, ImageFont, ImageOps
import re
from discord.ui import View, Select, Button



class UserProfile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    
    # === PROFILE COMMAND === 
    @app_commands.command(name="profile", description="Show your current points and rewards.")
    async def profile(
        self, 
        interaction: Interaction, 
        member: Optional[discord.Member] = None,
    ):
        await interaction.response.defer(ephemeral=False)
                
        with db_session() as session:
            if member is None:
                member = interaction.user
                        
            user = users_crud.get_or_create_user(session,member)

            user_discord_id = user.user_discord_id
            if user.nickname:
                display_name = user.nickname
            elif user.display_name:
                display_name = user.display_name
            elif user.username:
                display_name = user.username
                    
            points = user.points
            total_earned = user.total_earned
            
            title = (
                session.query(Inventory)
                .join(Reward)
                .filter(
                    Inventory.user_id == user.id,
                    Inventory.is_equipped,
                    Reward.reward_type == "title"
                ).first()
            )
            title_text = title.reward.reward_name if title else None
            
            rows = (
                session.query(Reward.emoji)
                .join(Inventory, Inventory.reward_id == Reward.id)
                .filter(
                    Inventory.user_id == user.id,
                    Inventory.is_equipped,
                    Reward.reward_type == "badge",
                ).all()
            )
            badge_emojis = [str(emoji) for (emoji,) in rows if emoji]
        
        async with aiohttp.ClientSession() as session_http:
            
            badge_icons = await extract_badge_icons(badge_emojis, session=session_http)
            
            avatar_url = member.display_avatar.url
            
            async with session_http.get(avatar_url) as resp:
                avatar_bytes = await resp.read()
        
        try:
            image_buffer = generate_profile_card(
                avatar_bytes,
                display_name,    
                points,
                total_earned,
                title_text,
                badge_icons
            )
            
            # === Send to user ===
            file = File(fp=image_buffer, filename="profile.png")
            await interaction.followup.send(file=file, ephemeral=False)

        except Exception as e:
            print("❌ Error in profile card generation:", e)
            await interaction.followup.send("❌ Something went wrong generating your profile card.", ephemeral=True)
        return
 
    
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
    @app_commands.command(name="equip_badge", description="Select up to 8 badges to display on your profile.")
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
    await bot.add_cog(UserProfile(bot))