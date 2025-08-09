from dataclasses import dataclass
from typing import Optional
import aiohttp
from discord import File

from db.database import db_session
from bot.crud import users_crud, inventory_crud
from bot.ui.renderers.badge_loader import extract_badge_icons
from bot.ui.renderers.profile_card import generate_profile_card
from bot.utils.discord_helpers import resolve_display_name

@dataclass
class ProfileVM:
    display_name: str
    points: int
    total_earned: int
    title_text: Optional[str]
    badge_emojis: list[str]
    avatar_url: str

def fetch_profile_vm(target_member) -> ProfileVM:
    with db_session() as dbs:
        user = users_crud.get_or_create_user(dbs, target_member)
        return ProfileVM(
            display_name=resolve_display_name(user),
            points=user.points,
            total_earned=user.total_earned,
            title_text=inventory_crud.get_equipped_title_name(dbs, user.id),
            badge_emojis=inventory_crud.get_equipped_badge_emojis(dbs, user.id),
            avatar_url=target_member.display_avatar.url,
        )

async def build_profile_file_and_name(vm: ProfileVM) -> tuple[File, str]:
    async with aiohttp.ClientSession() as http:
        badge_icons = await extract_badge_icons(vm.badge_emojis, session=http)
        async with http.get(vm.avatar_url) as resp:
            avatar_bytes = await resp.read()

    buf = generate_profile_card(
        avatar_bytes,
        vm.display_name,
        vm.points,
        vm.total_earned,
        vm.title_text,
        badge_icons,
    )
    return File(fp=buf, filename="profile.png"), vm.display_name