# bot/utils/discord_helpers.py
import discord
from discord import Message
from typing import Optional
from bot.config.constants import TRIGGER_TYPES
from bot.services.prompts_service import get_prompt_dto_by_code_and_event
from bot.services.action_events_service import get_action_event_dto_by_id

def resolve_display_name(user_row) -> str:
    """Returns the most relevant display name for a user."""
    # user_row is db.schema.User
    return user_row.nickname or user_row.display_name or user_row.username

## Announcement messages
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
            msg = f"{role_discord_id}\n{msg}"

        return await announcement_channel.send(msg)

    except Exception as e:
        print(f"⚠️ Failed to post message in channel: {e}")
        return None

def get_trigger_label(trigger_type: str) -> Optional[str]:
    for key, _group, label, _desc in TRIGGER_TYPES:
        if key == trigger_type:
            return label
    return trigger_type

def format_trigger_label(trigger_type: str, config: dict, event_id: int) -> str:
    desc_template = next(
        (desc for key, _, _, desc in TRIGGER_TYPES if key == trigger_type), 
        "Trigger"
    )

    x = config.get("min_count") or config.get("min_points") or config.get("min_days") or config.get("min_reports") or "X"
    y = ""

    if trigger_type == "prompt_repeat":
        code = config.get("prompt_code")
        if code:
            prompt = get_prompt_dto_by_code_and_event(code, event_id)
            if prompt:
                y = f'"{prompt.label}" ({prompt.code})'
            else:
                y = f'({code})'
    elif trigger_type == "action_repeat":
        ae_id = config.get("action_event_id")
        if ae_id:
            ae = get_action_event_dto_by_id(ae_id)
            if ae:
                y = f'"{ae.action_description}"'
            else:
                y = f'#{ae_id}'

    result = desc_template.replace("X", str(x)).replace("Y", y)
    return result