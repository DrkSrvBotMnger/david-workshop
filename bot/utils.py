from bot.config import MOD_ROLE_IDS
from discord import Interaction
from discord.app_commands import CheckFailure
from discord.ext.commands import check
import discord

def admin_or_mod_check():
    async def predicate(interaction: Interaction) -> bool:
        try:
            member = await interaction.guild.fetch_member(interaction.user.id)
        except discord.NotFound:
            return False

        return (
            member.guild_permissions.administrator or
            any(role.id in MOD_ROLE_IDS for role in member.roles)
        )
    return discord.app_commands.check(predicate)