import discord
from typing import Tuple, List

from db.database import db_session

# SERVICES
from bot.services.users_service import get_or_create_user_dto

# CRUD
from bot.crud.inventory_crud import fetch_user_titles_for_equip, fetch_user_badges_for_equip

def get_title_select_options(member: discord.abc.User | discord.Member) -> Tuple[int, List[discord.SelectOption]]:
    with db_session() as s:
        user = get_or_create_user_dto(s, member)
        rows = fetch_user_titles_for_equip(s, user.id)
    options: List[discord.SelectOption] = []
    for key, name, is_eq in rows:
        options.append(discord.SelectOption(label=(name or key), value=key, default=is_eq))
    return user.id, options

def get_badge_select_options(member: discord.abc.User | discord.Member) -> Tuple[int, List[discord.SelectOption]]:
    with db_session() as s:
        user = get_or_create_user_dto(s, member)
        rows = fetch_user_badges_for_equip(s, user.id)
    options: List[discord.SelectOption] = []
    for key, name, emoji, is_eq in rows:
        if emoji:
            options.append(discord.SelectOption(label=(name or key), value=key, emoji=str(emoji), default=is_eq))
        else:
            options.append(discord.SelectOption(label=(name or key), value=key, default=is_eq))
    return user.id, options
