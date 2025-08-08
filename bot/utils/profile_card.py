from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
from typing import List, Union

def generate_profile_card(
    user_avatar_bytes: bytes,
    display_name: str,
    points: int,
    total_earned: int,
    title: str,
    badges: List[Union[Image.Image, str]]
) -> io.BytesIO:
    """Generate a profile card image from real data with emoji or image badges."""
    base = Image.open("bot/assets/backgrounds/default_bg.png").convert("RGBA")
    draw = ImageDraw.Draw(base)

    try:
        font_path = "bot/assets/fonts/Finlandica-Medium.ttf"  # update to your font
        font_name = ImageFont.truetype("bot/assets/fonts/SofiaSansCondensed-Bold.ttf", 32)
        font_title = ImageFont.truetype("bot/assets/fonts/SofiaSansCondensed-Italic.ttf", 26)
        font_big = ImageFont.truetype(font_path, 24)
        font_small = ImageFont.truetype(font_path, 20)
        font_emoji = ImageFont.truetype(font_path, 40)
    except IOError:
        font_title = font_name = font_big = font_small = font_emoji = ImageFont.load_default()

    # Avatar
    avatar = Image.open(io.BytesIO(user_avatar_bytes)).resize((120, 120)).convert("RGBA")
    mask = Image.new("L", (120, 120), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 120, 120), fill=255)
    avatar.putalpha(mask)
    base.paste(avatar, (30, 30), avatar)

    # Display name + title
    draw.text((30, 170), display_name, font=font_name, fill="gold")
    if title:
        draw.text((30, 200), title, font=font_title, fill="gold")

    coin_path = "bot/assets/twemoji/1fa99.png"  # 🪙 coin
    coin_img = Image.open(coin_path).resize((20, 20)).convert("RGBA")
    bill_path = "bot/assets/twemoji/1f4b4.png"  # 💴 yen bill
    bill_img = Image.open(bill_path).resize((20, 20)).convert("RGBA")
    
    # Points
    draw.text((370, 40), "Vlachki", font=font_big, fill="gold", anchor="ra")
    draw.text((345, 80), f"{points} in wallet", font=font_small, fill="gold", anchor="ra")
    base.paste(coin_img, (350 , 80), coin_img)
    draw.text((345, 105), f"{total_earned} earned total", font=font_small, fill="gold", anchor="ra")
    base.paste(bill_img, (350 , 105), bill_img)

    # Badges
    draw.text((30, 240), "Badges", font=font_big, fill="gold")
    start_x, start_y = 30, 280
    spacing = 60
    for idx, badge in enumerate(badges[:12]):
        x = start_x + (idx % 6) * spacing
        y = start_y + (idx // 6) * spacing

        if isinstance(badge, Image.Image):
            badge_resized = badge.resize((40, 40))
            base.paste(badge_resized, (x, y), badge_resized)
        else:
            draw.text((x + 10, y), badge, font=font_emoji, fill="gold")

    # Output
    buffer = io.BytesIO()
    base.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
