from __future__ import annotations
from typing import Optional
from bot.config.constants import CUSTOM_DISCORD_EMOJI

def is_custom_emoji(s: Optional[str]) -> bool:
    """Check if a string is a custom Discord emoji (e.g. <:name:id>)."""
    return bool(s and CUSTOM_DISCORD_EMOJI.match(s))

def emoji_to_codepoint(emoji: str) -> str:
    """Convert a Unicode emoji into Twemoji codepoint format (e.g. '1f600')."""
    return "-".join(f"{ord(c):X}" for c in emoji).lower()