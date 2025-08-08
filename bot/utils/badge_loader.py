import re
import aiohttp
import io
from PIL import Image
from typing import List, Union
from bot.config import CUSTOM_DISCORD_EMOJI

def is_custom_emoji(s: str) -> bool:
    return bool(s and CUSTOM_DISCORD_EMOJI.match(s))

def emoji_to_codepoint(emoji: str) -> str:
    """Convert a Unicode emoji into Twemoji codepoint format."""
    return "-".join(f"{ord(c):X}" for c in emoji).lower()

async def extract_badge_icons(emojis: List[str], session: aiohttp.ClientSession) -> List[Union[Image.Image, str]]:
    """
    Given a list of emoji strings (custom or unicode),
    return a list of Pillow Image objects or emoji strings as fallback.
    """
    icons: List[Union[Image.Image, str]] = []

    for emoji in emojis:
        try:
            if is_custom_emoji(emoji):
                # Extract ID from <:name:id> or <a:name:id>
                emoji_id = emoji.rsplit(":", 1)[1][:-1]
                ext = "gif" if emoji.startswith("<a:") else "png"
                url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        img_bytes = await resp.read()
                        icons.append(Image.open(io.BytesIO(img_bytes)).convert("RGBA"))
                        continue  # move to next emoji
                    else:
                        print(f"⚠️ Failed to fetch custom emoji {emoji_id}: HTTP {resp.status}")
                        icons.append(emoji)
                        continue

            # Unicode emoji → Twemoji PNG
            code = emoji_to_codepoint(emoji)
            path = f"bot/assets/twemoji/{code}.png"
            try:
                icons.append(Image.open(path).convert("RGBA"))
            except FileNotFoundError:
                print(f"⚠️ No Twemoji PNG found for {emoji} ({code})")
                icons.append(emoji)

        except Exception as e:
            print(f"❌ Error processing {emoji}: {e}")
            icons.append(emoji or "❔")

    return icons