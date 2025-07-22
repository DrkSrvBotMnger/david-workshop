import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import uuid
import utils
from datetime import datetime
from typing import Literal
from admingroup import AdminGroup


TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.members = True  # needed for member info

bot = commands.Bot(command_prefix="!", intents=intents)


# /profile command
@bot.tree.command(name="profile", description="View your profile or someone else's.")
@app_commands.describe(user="Optional: select a user to view their profile")
async def profile(interaction: discord.Interaction, user: discord.Member = None):
    if user is None:
        user = interaction.user

    # Fetch and update user data
    user_data = utils.get_user_data(user)

    # Save updated display info
    utils.update_user_data(
        user.id,
        {**user_data,
         "nickname": user.nick,
         "display_name": user.global_name,
         "username": user.name}
    )

    warehouse = utils.get_warehouse()

    # Title info
    equipped_title = user_data.get("equipped_title")
    title_text = "No title equipped"
    if equipped_title:
        reward = next((r for r in warehouse if r["id"] == equipped_title and r["type"] == "title"), None)
        if reward:
            title_text = reward["name"]

    # Badges
    badge_ids = user_data.get("badges", [])
    badge_emojis = [
        r.get("emoji", "❔") for r in warehouse
        if r["id"] in badge_ids and r["type"] == "badge"
    ]
    badge_display = " ".join(badge_emojis) if badge_emojis else "No badges yet"

    # Display name
    display_name = user.display_name
    avatar_url = user.display_avatar.url

    # Embed
    embed = discord.Embed(title=f"{display_name}'s Profile", color=0xFFD700)
    embed.set_thumbnail(url=avatar_url)
    embed.add_field(name="🌟 Title", value=title_text, inline=False)
    embed.add_field(name="🏅 Badges", value=badge_display, inline=False)
    embed.add_field(name="💰 Vlachka", value=user_data['points'], inline=False)

    await interaction.response.send_message(embed=embed)

# /eventlist - Quick overview
@bot.tree.command(name="eventlist", description="List all events with summary info.")
async def eventlist(interaction: discord.Interaction):

    events = utils.get_events()
    if not events:
        await interaction.response.send_message("📭 No events found.", ephemeral=True)
        return

    embed = discord.Embed(title="📋 Events Overview", color=discord.Color.blue())
    for event in sorted(events, key=lambda e: e.get("start_date")):
        name = event.get("name", "Unnamed")
        event_description = event.get("description", "n/a")
        eid = event.get("event_id", event.get("id"))
        start_date = event.get("start_date", "N/A")
        reward_count = len(event.get("rewards", []))
        embed.add_field(
            name=f"📛 {name} (`{eid}`)",
            value=f"🔤 `{event_description}` • 🎁 `{reward_count}` rewards\n Starts on {start_date}",
            inline=False
        )
    await interaction.response.send_message(embed=embed, ephemeral=False)


@bot.tree.command()
async def roadmap(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛠️ Workshop Progress Tracker",
        description="Here's what was built so far and what's next for the event + reward system!",
        color=0x2ECC71
    )    
    
    embed.add_field(
        name="✅ Features Completed",
        value=(
            "**🔐 Admin Tools**\n"
            "• Reward creation, editing, deletion (with logs)\n"
            "• Manual reward grants, fixed stacking logic\n"
            "• Reward info panel with metadata and linked events\n"
            "• Warehouse listing (paginated, with event links)\n"
            "• Reward <--> Event linking + unlinking\n\n"
            "**🗓️ Event System**\n"
            "• Create/edit/delete events with full metadata\n"
            "• Event logs (filtered by mod, paginated)\n"
            "• Event overview menu (1/page) with filters\n"
            "• Quick `/listevents` for a bird’s-eye view\n\n"
            "**📁 Data + Logs**\n"
            "• All objects include created/edited metadata\n"
            "• Safe JSON handling and auto-fix on load errors\n"
            "• Embed paginator utility for reusable pagination\n"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🔜 Still To Do",
        value=(
            "• 🛍️ Member shop: filter by active event, buy with points\n"
            "• 🎭 Use items (incl. consuming stackables)\n"
            "• 👤 Update profiles to store stackable item quantity\n"
            "• 🖼️ Public `/eventinfo` (cosmetic + data) for 1 event\n"
            "• 👀 Respect `visible: false` flag on public views\n"
            "• 🧹 View and clean profiles for deleted users\n"
            "• 🧾 Sort rewards, events, logs in consistent ways\n"
            "• ✨ Cosmetic polish for embeds and command outputs"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚠️ And Of Course...",
        value="...anything else we think of along the way. 😅",
        inline=False
    )
    
    embed.set_footer(text="David's Workshop • Progress as of July 12 2025")


    await interaction.response.send_message(embed=embed, ephemeral=False)




# Load admin commands
admin_group = AdminGroup()
bot.tree.add_command(admin_group)


# When bot is ready
@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)

# Run bot
bot.run(TOKEN)