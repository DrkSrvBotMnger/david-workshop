import discord
from discord import Message
from typing import Optional

def resolve_display_name(user_row) -> str:
    """Returns the most relevant display name for a user."""
    # user_row is db.schema.User
    return user_row.nickname or user_row.display_name or user_row.username

async def post_announcement_message(
    interaction: discord.Interaction, 
    announcement_channel_id: str,
    msg: str,
    role_discord_id: Optional[str] = None
) -> Optional[Message]:
    """Post announcement in announcement channel"""

    try:
        announcement_channel = interaction.guild.get_channel(int(announcement_channel_id))
        if not announcement_channel:
            print(f"⚠️ Announcement channel {announcement_channel_id} not found.")
            return None

        # Add role ping if applicable
        if role_discord_id:
            msg = f"<@&{role_discord_id}>\n{msg}"

        return await announcement_channel.send(msg)

    except Exception as e:
        print(f"⚠️ Failed to post message in channel: {e}")
        return None