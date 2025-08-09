# bot/cogs/mod_actions_review.py
from discord import app_commands, Interaction, Embed, Member, File
from discord.ext import commands
from io import StringIO
from datetime import datetime, timedelta, timezone
from db.database import db_session
from db.schema import User, UserAction, ActionEvent, Event
from bot.utils.time_parse_paginate import admin_or_mod_check  # your existing check

class ModActionsReview(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    mod = app_commands.Group(name="mod", description="Moderator utilities")

    @admin_or_mod_check()
    @mod.command(name="actions_review", description="List actions done and export submitted URLs.")
    @app_commands.describe(
        event="Filter by event (name or key, contains match)",
        member="Filter by user",
        days="Only include actions from the last N days (default 30)"
    )
    async def actions_review(
        self,
        interaction: Interaction,
        event: str | None = None,
        member: Member | None = None,
        days: int | None = 30
    ):
        since = datetime.now(timezone.utc) - timedelta(days=days or 30)

        with db_session() as session:
            q = (
                session.query(UserAction, User, ActionEvent, Event)
                .join(User, User.id == UserAction.user_id)
                .join(ActionEvent, ActionEvent.id == UserAction.action_event_id)
                .join(Event, Event.id == ActionEvent.event_id)
                .filter(UserAction.created_at >= since.isoformat())  # adjust if stored as datetime vs string
                .order_by(UserAction.created_at.desc())
            )

            if member:
                q = q.filter(User.user_discord_id == str(member.id))

            if event:
                like = f"%{event}%"
                q = q.filter((Event.event_key.ilike(like)) | (Event.name.ilike(like)))

            rows = q.all()

            # Collect for display + export (only rows with a URL for the URL list)
            url_rows = []
            total = len(rows)
            for ua, u, ae, ev in rows:
                if getattr(ua, "url", None):
                    url_rows.append({
                        "created_at": getattr(ua, "created_at", ""),
                        "user": u.display_name or u.username,
                        "user_id": u.user_discord_id,
                        "event": ev.name or ev.event_key,
                        "action_event": ae.action_event_key,
                        "url": ua.url
                    })

        # Summary embed
        embed = Embed(title="Actions Review")
        embed.add_field(name="Total actions", value=str(total), inline=True)
        embed.add_field(name="With URL", value=str(len(url_rows)), inline=True)
        if event:
            embed.add_field(name="Event filter", value=event, inline=False)
        if member:
            embed.add_field(name="User filter", value=member.display_name, inline=False)
        embed.add_field(name="Since", value=since.strftime("%Y-%m-%d"), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Send URL export if any
        if url_rows:
            # CSV
            sio = StringIO()
            sio.write("created_at,user,user_id,event,action_event,url\n")
            for r in url_rows:
                # naive CSV escaping for commas/quotes
                def esc(s: str): 
                    s = str(s or "")
                    if any(ch in s for ch in [",", "\"", "\n"]):
                        return '"' + s.replace('"', '""') + '"'
                    return s
                line = ",".join([esc(r[k]) for k in ["created_at","user","user_id","event","action_event","url"]])
                sio.write(line + "\n")
            sio.seek(0)
            await interaction.followup.send(
                content="Here are the submitted URLs (CSV).",
                file=File(fp=sio, filename="submitted_urls.csv"),
                ephemeral=True
            )
        else:
            await interaction.followup.send("No submitted URLs found for this filter.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ModActionsReview(bot))
