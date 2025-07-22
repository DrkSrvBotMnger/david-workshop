from config import MOD_ROLE_IDS
import discord

def is_moderator(member: discord.Member) -> bool:
    return (any(role.id in MOD_ROLE_IDS for role in member.roles))
