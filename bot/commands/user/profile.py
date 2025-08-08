import discord
from discord import app_commands, File, Interaction, Embed, User as DiscordUser, SelectOption
from typing import Optional, List, Union
from discord.ext import commands
from bot.crud import events_crud, users_crud
from db.database import db_session
from db.schema import EventStatus, Inventory, Reward, User
from bot.config import TICKET_CHANNEL_ID
from bot.utils.profile_card import generate_profile_card  # path depends on your structure
from bot.utils.badge_loader import extract_badge_icons
from bot.utils.time_parse_paginate import now_iso
from bot.ui.user.event_button import EventButtons
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
    @app_commands.describe(shortcode="Shortcode of the event to view")
    @app_commands.command(name="event", description="View details for a visible event.")
    async def view_event(
        self,
        interaction: discord.Interaction,
        shortcode: str
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)
    
        with db_session() as session:
            event = events_crud.get_event_by_key(session, shortcode)
            if not event:
                await interaction.followup.send(f"❌ Event `{shortcode}` not found.", ephemeral=True)
                return
    
            if event.event_status == EventStatus.draft:
                await interaction.followup.send(f"⚠️ Event `{shortcode}` is not currently visible.", ephemeral=True)
                return
    
            if not event.embed_message_discord_id:
                await interaction.followup.send(
                    f"❌ Event `{shortcode}` is visible but no embed message is set.",
                    ephemeral=True
                )
                return
    
            try:
                channel = interaction.guild.get_channel(int(event.embed_channel_discord_id))
                if not channel:
                    raise ValueError("Channel not found")
    
                message = await channel.fetch_message(int(event.embed_message_discord_id))
                if not message.embeds:
                    raise ValueError("No embeds in stored message")
    
                # Build buttons with correct guild-specific ticket link
                view = EventButtons(event.event_key, event.event_name)
                for child in view.children:
                    if isinstance(child, discord.ui.Button) and child.style == discord.ButtonStyle.link:
                        child.url = f"https://discord.com/channels/{interaction.guild.id}/{TICKET_CHANNEL_ID}"
    
                # Send all embeds + buttons (ephemeral for spam control)
                await interaction.followup.send(
                    embeds=message.embeds,
                    view=view
                )
    
            except Exception as e:
                print(f"⚠️ Failed to fetch event embed for {shortcode}: {e}")
                await interaction.followup.send(
                    f"❌ Could not retrieve the embed for `{shortcode}`. Please contact a moderator.",
                    ephemeral=True
                )


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