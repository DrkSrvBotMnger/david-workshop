# bot/utils/permissions.py
import discord
from discord import app_commands, Interaction
from bot.config import MOD_ROLE_IDS

async def is_admin_or_mod(interaction: Interaction) -> bool:
    """True if invoker is admin or has any role in MOD_ROLE_IDS."""
    try:
        if interaction.guild is None:
            return False
        member = await interaction.guild.fetch_member(interaction.user.id)
    except discord.NotFound:
        return False

    return (
        member.guild_permissions.administrator
        or any(role.id in MOD_ROLE_IDS for role in member.roles)
    )

def admin_or_mod_check():
    """Decorator for app commands that require admin or mod."""
    return app_commands.check(is_admin_or_mod)