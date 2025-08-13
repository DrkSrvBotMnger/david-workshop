import discord
from discord import app_commands, Interaction, Embed
from discord.ext import commands
from typing import Optional

from sqlalchemy.sql.base import _exclusive_against
from bot.crud import events_crud, action_events_crud, reward_events_crud
from bot.config import EVENT_ANNOUNCEMENT_CHANNEL_ID, EVENTS_PER_PAGE, LOGS_PER_PAGE, EVENT_TYPES
from bot.utils.time_parse_paginate import admin_or_mod_check, safe_parse_date, confirm_action, paginate_embeds, format_discord_timestamp, format_log_entry, parse_message_link, post_announcement_message
from db.database import db_session
from db.schema import EventLog, EventStatus, ActionEvent, Action
from bot.ui.admin.event_dashboard_view import EventDashboardView, build_event_embed
from io import StringIO, BytesIO
import csv
from collections import defaultdict
from typing import Iterable

from bot.crud import reports_crud  # <-- NEW


# --- NEW: Picker UI for /admin_event show ---

from dataclasses import dataclass

PAGE_SIZE = 25  # Discord select max


# If you don't already have this:
try:
    from bot.utils.parsing import safe_parse_date  # noqa
except Exception:
    from datetime import datetime
    def safe_parse_date(s: str) -> str | None:
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return s
        except Exception:
            return None

def _group_by_action(rows: list[dict]) -> dict[str, list[dict]]:
    g: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        g[r.get("action_key") or "unknown"].append(r)
    return g

def _group_by_user(rows: list[dict]) -> dict[str, list[dict]]:
    """
    Key by user mention when possible; fallback to display_name.
    """
    g: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        mention = f"<@{r['user_discord_id']}>" if r.get("user_discord_id") else None
        key = mention or r.get("display_name") or "Unknown User"
        g[key].append(r)
    return g

def _make_report_pages_group_by_action(rows: list[dict], *, title: str) -> list[discord.Embed]:
    pages: list[discord.Embed] = []
    grouped = _group_by_action(rows)
    items = sorted(grouped.items(), key=lambda kv: kv[0])
    def new_embed():
        return discord.Embed(title=title, color=discord.Color.green()).set_footer(text="Grouped by Action")
    emb, count = new_embed(), 0
    for action_key, bucket in items:
        lines = []
        for r in bucket:
            stamp = r["created_at"]
            who = f"<@{r['user_discord_id']}>" if r.get("user_discord_id") else r.get("display_name", "Unknown")
            url = r.get("url")
            extra = []
            if r.get("numeric_value") is not None: extra.append(str(r["numeric_value"]))
            if r.get("text_value"): extra.append(str(r["text_value"])[:60])
            if r.get("boolean_value") is not None: extra.append("✅" if r["boolean_value"] else "❌")
            suffix = f"  ({' | '.join(extra)})" if extra else ""
            lines.append(f"• {who} — {url}{suffix}  ({stamp})" if url else f"• {who}{suffix}  ({stamp})")
        emb.add_field(name=f"{action_key} ({len(bucket)})", value=("\n".join(lines)[:1024] or "—"), inline=False)
        count += 1
        if count >= 25:
            pages.append(emb)
            emb, count = new_embed(), 0
    if count or not pages:
        pages.append(emb)
    return pages

def _make_report_pages_group_by_user(rows: list[dict], *, title: str) -> list[discord.Embed]:
    pages: list[discord.Embed] = []
    grouped = _group_by_user(rows)
    items = sorted(grouped.items(), key=lambda kv: kv[0].lower())
    def new_embed():
        return discord.Embed(title=title, color=discord.Color.green()).set_footer(text="Grouped by User")
    emb, count = new_embed(), 0
    for user_key, bucket in items:
        lines = []
        for r in bucket:
            stamp = str(r.get("created_at", ""))
            action_key = r.get("action_key") or "unknown"
            url = r.get("url")
            extra = []
            if r.get("numeric_value") is not None: extra.append(str(r["numeric_value"]))
            if r.get("text_value"): extra.append(str(r["text_value"])[:60])
            if r.get("boolean_value") is not None: extra.append("✅" if r["boolean_value"] else "❌")
            suffix = f"  ({' | '.join(extra)})" if extra else ""
            lines.append(f"• {action_key} — {url}{suffix}  ({stamp})" if url else f"• {action_key}{suffix}  ({stamp})")
        emb.add_field(name=f"{user_key} ({len(bucket)})", value=("\n".join(lines)[:1024] or "—"), inline=False)
        count += 1
        if count >= 25:
            pages.append(emb)
            emb, count = new_embed(), 0
    if count or not pages:
        pages.append(emb)
    return pages



def _iso_window(date_from: str | None, date_to: str | None) -> tuple[str | None, str | None]:
    """Turn YYYY-MM-DD into inclusive ISO boundaries for lexicographic comparisons."""
    df = f"{date_from}T00:00:00" if date_from else None
    dt = f"{date_to}T23:59:59" if date_to else None
    return df, dt

def _resolve_event_key(session, value: str | None) -> str | None:
    """
    Accepts either an event key (shortcode) or an exact event name.
    Returns the event_key or None if not found/None.
    """
    if not value:
        return None

    # Try key
    ev = events_crud.get_event_by_key(session, value)
    if ev:
        return ev.event_key

    # Try exact name
    from db.schema import Event
    by_name = session.query(Event).filter(Event.event_name == value).first()
    return by_name.event_key if by_name else None



def _make_report_pages(
    rows: list[dict],
    *,
    title: str,
    group_label: str = "By Action",
) -> list[discord.Embed]:
    """
    Build paginated embeds grouped by action. One field per action group.
    Splits across multiple embeds if >25 fields.
    """
    pages: list[discord.Embed] = []
    grouped = _group_by_action(rows)
    items = sorted(grouped.items(), key=lambda kv: kv[0])

    def new_embed() -> discord.Embed:
        return discord.Embed(title=title, color=discord.Color.green()).set_footer(text=group_label)

    emb = new_embed()
    fields_in_emb = 0

    for action_key, bucket in items:
        # Build the field body
        # Example row line: • <@123> — https://fic.link  (2025-08-10 13:33)
        # If URL missing, still show user + created time
        lines: list[str] = []
        for r in bucket:
            stamp = str(r.get("created_at", ""))
            who = f"<@{r['user_discord_id']}>" if r.get("user_discord_id") else r.get("display_name", "Unknown")
            url = r.get("url")
            extra_bits = []

            # include light extra data if present
            if r.get("numeric_value") is not None:
                extra_bits.append(str(r["numeric_value"]))
            if r.get("text_value"):
                # avoid blowing the embed; trim small
                extra_bits.append(r["text_value"][:60])
            if r.get("boolean_value") is not None:
                extra_bits.append("✅" if r["boolean_value"] else "❌")

            suffix = f"  ({' | '.join(extra_bits)})" if extra_bits else ""
            if url:
                lines.append(f"• {who} — {url}{suffix}  ({stamp})")
            else:
                lines.append(f"• {who}{suffix}  ({stamp})")

        val = "\n".join(lines) if lines else "—"
        name = f"{action_key} ({len(bucket)})"
        emb.add_field(name=name, value=val[:1024] or "—", inline=False)
        fields_in_emb += 1

        if fields_in_emb >= 25:
            pages.append(emb)
            emb = new_embed()
            fields_in_emb = 0

    if fields_in_emb > 0 or not pages:
        pages.append(emb)
    return pages


class ReportResultsView(discord.ui.View):
    """
    Buttons: Post in channel, Export CSV, Toggle group (Action/User).
    Holds raw rows so it can rebuild pages when toggling.
    """
    def __init__(self, *, rows: list[dict], title: str, csv_bytes: bytes, initial_group: str = "action"):
        super().__init__(timeout=180)
        self.rows = rows
        self.title = title
        self.csv_bytes = csv_bytes
        self.group_mode = initial_group  # "action" | "user"
        self.pages: list[discord.Embed] = self._build_pages()

        # Initialize toggle button label to current opposite
        self.group_toggle.label = "Group by: User" if self.group_mode == "action" else "Group by: Action"

    def _build_pages(self) -> list[discord.Embed]:
        if self.group_mode == "user":
            return _make_report_pages_group_by_user(self.rows, title=self.title)
        return _make_report_pages_group_by_action(self.rows, title=self.title)

    async def on_timeout(self):
        for c in self.children:
            if hasattr(c, "disabled"):
                c.disabled = True  # type: ignore[attr-defined]
        # Can't reliably edit ephemeral after timeout; ignore.

    @discord.ui.button(label="Post in this channel", style=discord.ButtonStyle.primary, row=0)
    async def post_here(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Defer first to avoid 3s timeout
        await interaction.response.defer(ephemeral=True, thinking=False)
        max_pages = 3
        for emb in self.pages[:max_pages]:
            await interaction.channel.send(embed=emb)
        if len(self.pages) > max_pages:
            await interaction.channel.send(f"…and **{len(self.pages) - max_pages}** more page(s).")
        await interaction.followup.send("✅ Posted.", ephemeral=True)

    @discord.ui.button(label="Export CSV", style=discord.ButtonStyle.secondary, row=0)
    async def export_csv(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=False)
        file = discord.File(BytesIO(self.csv_bytes), filename="actions_report.csv")
        await interaction.followup.send(content="Here’s your CSV:", file=file, ephemeral=True)

    @discord.ui.button(label="Group by: User", style=discord.ButtonStyle.secondary, row=1)
    async def group_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Quick edit; no need to defer
        self.group_mode = "user" if self.group_mode == "action" else "action"
        self.pages = self._build_pages()
        button.label = "Group by: User" if self.group_mode == "action" else "Group by: Action"
        # Update the ephemeral message with the first page
        await interaction.response.edit_message(embed=self.pages[0], view=self)



@dataclass
class _EventRow:
    key: str
    name: str
    status: str
    priority: int
    modified_at: str | None
    created_at: str

def _load_events(session, status_filter: str | None) -> list[_EventRow]:
    """Fetch and map events for the picker."""
    events = events_crud.get_all_events(
        session=session,
        tag=None,
        event_status=status_filter,   # expects 'draft'|'visible'|'active'|'archived' or None
        mod_by_discord_id=None
    )
    rows: list[_EventRow] = []
    for e in events:
        rows.append(
            _EventRow(
                key=e.event_key,
                name=e.event_name,
                status=e.event_status.value,
                priority=e.priority or 0,
                modified_at=e.modified_at,
                created_at=e.created_at,
            )
        )
    # Sort most-recent first (match list command’s feel)
    rows.sort(key=lambda r: (r.modified_at or r.created_at, r.priority), reverse=True)
    return rows

class AdminEventPickerView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, guild_id: int | None):
        super().__init__(timeout=180)
        self.interaction = interaction
        self.guild_id = guild_id
        self.status_filter: str | None = None  # None = All
        self.page: int = 0
        self.rows: list[_EventRow] = []
        self._event_select: discord.ui.Select | None = None
        self._status_select: discord.ui.Select | None = None
        self._prev_btn: discord.ui.Button | None = None
        self._next_btn: discord.ui.Button | None = None

        # Build controls
        self._status_select = discord.ui.Select(
            placeholder="Filter by status…",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="All", value="__all__", emoji="📋"),
                discord.SelectOption(label="Draft", value="draft", emoji="📝"),
                discord.SelectOption(label="Visible", value="visible", emoji="👁️"),
                discord.SelectOption(label="Active", value="active", emoji="🎉"),
                discord.SelectOption(label="Archived", value="archived", emoji="📦"),
            ],
        )
        self._status_select.callback = self._on_status_changed
        self.add_item(self._status_select)

        self._event_select = discord.ui.Select(
            placeholder="Pick an event…",
            min_values=1,
            max_values=1,
            options=[],  # filled by _refresh_options
        )
        self._event_select.callback = self._on_event_picked
        self.add_item(self._event_select)

        self._prev_btn = discord.ui.Button(label="Prev", style=discord.ButtonStyle.secondary)
        self._next_btn = discord.ui.Button(label="Next", style=discord.ButtonStyle.secondary)
        self._prev_btn.callback = self._on_prev
        self._next_btn.callback = self._on_next
        self.add_item(self._prev_btn)
        self.add_item(self._next_btn)

    async def on_timeout(self) -> None:
        for c in self.children:
            if hasattr(c, "disabled"):
                c.disabled = True  # type: ignore[attr-defined]
        try:
            await self.interaction.edit_original_response(view=self)
        except Exception:
            pass

    async def refresh(self):
        """Reload data from DB, clamp page, rebuild options and button states."""
        from db.database import db_session  # local import to avoid cycles
        with db_session() as session:
            self.rows = _load_events(session, self.status_filter)

        total = len(self.rows)
        max_page = 0 if total == 0 else (total - 1) // PAGE_SIZE
        self.page = max(0, min(self.page, max_page))

        # Build current page options
        if total == 0:
            options = [
                discord.SelectOption(label="No events found for this filter", value="__none__", description="")
            ]
            self._event_select.options = options
            self._event_select.disabled = True
        else:
            start = self.page * PAGE_SIZE
            chunk = self.rows[start:start + PAGE_SIZE]
            options = []
            for r in chunk:
                label = r.name[:100]  # Discord limit
                desc = f"{r.key} • {r.status.capitalize()}"
                options.append(discord.SelectOption(label=label, value=r.key, description=desc))
            self._event_select.options = options
            self._event_select.disabled = False

        # Buttons state
        self._prev_btn.disabled = (self.page <= 0 or total == 0)
        self._next_btn.disabled = (total == 0 or (self.page + 1) * PAGE_SIZE >= total)

    async def _on_status_changed(self, interaction: discord.Interaction):
        val = self._status_select.values[0]
        self.status_filter = None if val == "__all__" else val
        self.page = 0
        await self.refresh()
        await interaction.response.edit_message(view=self)

    async def _on_prev(self, interaction: discord.Interaction):
        if self.page > 0:
            self.page -= 1
            await self.refresh()
        await interaction.response.edit_message(view=self)

    async def _on_next(self, interaction: discord.Interaction):
        self.page += 1
        await self.refresh()
        await interaction.response.edit_message(view=self)

    async def _on_event_picked(self, interaction: discord.Interaction):
        """Load the dashboard for the picked event and swap the view."""
        picked_key = self._event_select.values[0]
        if picked_key == "__none__":
            await interaction.response.defer()
            return

        from db.database import db_session
        from bot.crud import action_events_crud, reward_events_crud

        # Fetch full metadata
        with db_session() as session:
            event = events_crud.get_event_by_key(session, event_key=picked_key)
            if not event:
                await interaction.response.send_message(f"❌ Event `{picked_key}` not found anymore.", ephemeral=True)
                return

            event_data = {
                "event_name": event.event_name,
                "event_key": event.event_key,
                "start_date": event.start_date,
                "end_date": event.end_date,
                "tags": event.tags,
                "event_description": event.event_description,
                "created_by": event.created_by,
                "created_at": event.created_at,
                "modified_by": event.modified_by,
                "modified_at": event.modified_at,
                "priority": event.priority,
                "coordinator_discord_id": event.coordinator_discord_id,
                "role_discord_id": event.role_discord_id,
                "embed_message_discord_id": event.embed_message_discord_id,
                "embed_channel_discord_id": event.embed_channel_discord_id,
                "event_status": event.event_status.value,
                "event_type": event.event_type
            }

            # --- Actions: keep only ACTIVE actions ---
            action_events = action_events_crud.get_action_events_for_event(session, event.id)
            actions_data = []
            for ae in action_events:
                # Hide deactivated actions (e.g., your old v1s)
                if not (ae.action and getattr(ae.action, "is_active", False)):
                    continue
    
                actions_data.append({
                    "action_key": ae.action.action_key if ae.action else None,
                    "variant": ae.variant,
                    "points_granted": ae.points_granted,
                    "reward_event_key": ae.reward_event.reward_event_key if ae.reward_event else None,
                    "is_allowed_during_visible": ae.is_allowed_during_visible,
                    "is_self_reportable": ae.is_self_reportable,
                    "input_help_json": ae.input_help_json or None,
                })
    
            # --- Rewards: add info about linked actions (for onaction availability) ---
            reward_events = reward_events_crud.get_all_reward_events_for_event(session, event.id)
            rewards_data = []
            for re in reward_events:
                # Get the single ActionEvent (if any) that owns this reward_event
                link = (
                    session.query(ActionEvent.variant, Action.action_key)
                    .outerjoin(Action, Action.id == ActionEvent.action_id)
                    .filter(ActionEvent.reward_event_id == re.id)
                    .first()
                )
                linked_variant, linked_key = (None, None)
                if link:
                    linked_variant, linked_key = link  # (variant, action_key)
    
                rewards_data.append({
                    "reward_name": re.reward.reward_name,
                    "reward_key": re.reward.reward_key if re.reward else None,
                    "price": re.price,
                    "availability": re.availability,   # "inshop" | "onaction"
                    "linked_action_key": linked_key,   # SINGLE
                    "linked_variant": linked_variant,  # SINGLE
                })
            
        # Swap to dashboard
        dashboard = EventDashboardView(event_data, actions_data, rewards_data, self.guild_id)
        embed = build_event_embed(event_data, self.guild_id)
        await interaction.response.edit_message(embed=embed, view=dashboard)


class AdminEventCommands(commands.GroupCog, name="admin_event"):
    """Admin commands for managing events."""
    def __init__(self, bot):
        self.bot = bot

    
    # === CREATE EVENT ===
    @admin_or_mod_check()
    @app_commands.describe(
        shortcode="Shortcode for the event (date auto-added: YYMM)",
        event_type="Type of event (freeform or prompt)",
        name="Full name of the event",
        description="Public-facing description",
        start_date="Start date (YYYY-MM-DD)",
        end_date="End date (YYYY-MM-DD) (optional)",
        coordinator="Optional mod managing the event, defaults to you",
        priority="Order to display in listings (higher = higher)",
        tags="Comma-separated tags (e.g. rp, halloween) (optional)",
        message_link="Link to the message containing the display embed (optional)",
        role_id = "Discord role id to tag during announcements (optional)"
        )
    @app_commands.command(name="create", description="Create a new event.")
    async def create_event(
        self,
        interaction: discord.Interaction,
        shortcode: str,
        name: str,
        description: str,
        start_date: str,
        event_type: Optional[str] = "freeform",  
        end_date: Optional[str] = None,
        coordinator: Optional[discord.Member] = None,
        priority: int = 0,
        tags: Optional[str] = None,
        message_link: Optional[str] = None,
        role_id: Optional[str] = None
    ):
        """Creates an event. Event key is auto-generated from shortcode + start month."""

        await interaction.response.defer(thinking=True, ephemeral=True)

        if event_type not in EVENT_TYPES:
            event_type = "freeform"
        
        
        # Handle date parsing
        start_date_parsed = safe_parse_date(start_date)
        if not start_date_parsed:
            await interaction.followup.send("❌ Invalid start date format. Use YYYY-MM-DD.")
            return
        if end_date:
            end_date_parsed = safe_parse_date(end_date)
            if not end_date_parsed:
                await interaction.followup.send("❌ Invalid end date format. Use YYYY-MM-DD or leave empty.")
                return
        else:
            end_date_parsed = None

        # Auto-generate event_key
        event_key = f"{shortcode.lower()}{start_date_parsed[2:4]}{start_date_parsed[5:7]}"

        # Handle coordinator
        if coordinator:
            coordinator_id = str(coordinator.id)
            coordinator_display = coordinator.mention
        else:
            coordinator_id = str(interaction.user.id)
            coordinator_display = interaction.user.mention

        # Handle tags and embed channel
        tag_str = tags.lower().strip() if tags else None
        
        if priority < 0:
            await interaction.followup.send("❌ Priority must be a non-negative integer.")
            return

        # Parse message link
        if message_link:
            embed_channel_discord_id, embed_message_discord_id = parse_message_link(message_link)
        else:
            embed_channel_discord_id = None
            embed_message_discord_id = None
        
        # Check for existing event_id then create event
        try:
            with db_session() as session:    
                existing_event = events_crud.get_event_by_key(
                    session=session, 
                    event_key=event_key
                )
                if existing_event:
                    await interaction.followup.send(
                        f"❌ An event with shortcode `{event_key}` already exists. Choose a different shortcode or start date."
                    )
                    return

                event_create_data ={
                    "event_key": event_key,
                    "event_name": name,
                    "event_type": event_type,
                    "event_description": description,
                    "start_date": start_date_parsed,
                    "end_date": end_date_parsed,
                    "created_by": str(interaction.user.id),
                    "coordinator_discord_id": coordinator_id,
                    "priority": priority,
                    "tags": tag_str,
                    "embed_channel_discord_id": embed_channel_discord_id,
                    "embed_message_discord_id": embed_message_discord_id,
                    "role_discord_id": role_id                    
                }
                    
                event = events_crud.create_event(
                    session=session,
                    event_create_data=event_create_data
                )
                
                # Extract now while session is open
                safe_event_name = event.event_name

        except Exception as e:
            print(f"❌ DB failure: {e}")
            await interaction.followup.send("❌ An unexpected error occurred.")
            return

        msg = f"✅ Event `{safe_event_name}` created with shortcode `{event_key}`.\n👤 Coordinator: {coordinator_display}"
        if not coordinator:
            msg += " *(defaulted to you)*"

        await interaction.followup.send(content=msg)


    # === EDIT EVENT ===
    @admin_or_mod_check()
    @app_commands.describe(
        shortcode="Shortcode of the event to edit",
        name="New full name (optional)",
        description="New description (optional)",
        start_date="New start date (YYYY-MM-DD)",
        end_date="New end date (YYYY-MM-DD, use CLEAR to remove)",
        coordinator="New coordinator (optional)",
        tags="New comma-separated tags (use CLEAR to remove)",
        priority="Updated display priority (use CLEAR to remove)",
        message_link="New message link to display (use CLEAR to remove)",
        role_id = "New discord role id to tag during announcements (use CLEAR to remove)",
        reason="Optional reason for editing (will be logged)"
    )
    @app_commands.command(name="edit", description="Edit an existing event's metadata.")
    async def edit_event(
        self,
        interaction: discord.Interaction,
        shortcode: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        coordinator: Optional[discord.Member] = None,
        tags: Optional[str] = None,
        priority: Optional[int] = None,
        message_link: Optional[str] = None,
        role_id: Optional[discord.Role] = None,
        reason: Optional[str] = None
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        # Check for existing event_id then update event
        with db_session() as session:
            event = events_crud.get_event_by_key(
                session=session, 
                event_key=shortcode    
            )
            if not event:
                await interaction.followup.send(f"❌ Event `{shortcode}` not found.")
                return

            # Prevent editing active events							   
            if event.event_status == EventStatus.active:
                await interaction.followup.send("⚠️ This event is active and cannot be edited. Use a separate command to deactivate it first.")
                return

    # Handle date parsing and CLEAR sentinel
            start_date_parsed = safe_parse_date(start_date) if start_date else None
            if start_date and not start_date_parsed:
                await interaction.followup.send("❌ Invalid start date format. Use YYYY-MM-DD.")
                return

            if end_date and end_date.strip().upper() != "CLEAR":
                end_date_parsed = safe_parse_date(end_date)
                if not end_date_parsed:
                     await interaction.followup.send("❌ Invalid end date format. Use YYYY-MM-DD or CLEAR to remove it.")
                     return
            else:
                end_date_parsed = None

            event_update_data = {}
            if name: 
                event_update_data["event_name"] = name
            if description: 
                event_update_data["event_description"] = description
            if start_date_parsed: 
                event_update_data["start_date"] = start_date_parsed
            if end_date:
                event_update_data["end_date"] = None if end_date.strip().upper() == "CLEAR" else end_date_parsed
            if coordinator: 
                event_update_data["coordinator_discord_id"] = str(coordinator.id)
            if tags:
                if tags.strip().upper() == "CLEAR":
                    event_update_data["tags"] = None
                else:
                    event_update_data["tags"] = ",".join(tag.strip() for tag in tags.split(","))            
            if message_link: 
                if message_link.strip().upper() == "CLEAR":
                    if event.event_status == EventStatus.visible:
                        await interaction.followup.send("❌ You cannot remove the embed message while the event is visible. Hide it first.")
                        return
                    event_update_data["embed_channel_discord_id"] = None
                    event_update_data["embed_message_discord_id"] = None
                else:
                    embed_channel_discord_id, embed_message_discord_id = parse_message_link(message_link)
                    event_update_data["embed_channel_discord_id"] = embed_channel_discord_id
                    event_update_data["embed_message_discord_id"] = embed_message_discord_id
            if role_id:
                if role_id.strip().upper() == "CLEAR":
                    event_update_data["role_discord_id"] = None 
                else: 
                    event_update_data["role_discord_id"] = role_id.strip()
            if priority:
                if priority.strip().upper() == "CLEAR":
                    event_update_data["priority"] = 0
                else:
                    try:
                        val = int(priority)
                        if val < 0:
                            raise ValueError
                        event_update_data["priority"] = val
                    except ValueError:
                        await interaction.followup.send("❌ Priority must be a non-negative integer or CLEAR.")
                        return

            if not event_update_data:
                await interaction.followup.send("❌ No valid fields provided to update.")
                return

            event_update_data["modified_by"] = str(interaction.user.id)
            
            events_crud.update_event(
                session=session,
                event_key=shortcode,
                event_update_data=event_update_data,
                reason=reason
            )

            # Extract now while session is open								   
            safe_event_name = event.event_name

        await interaction.followup.send(
            f"✅ Event `{safe_event_name} ({shortcode})` updated successfully." + (f"\n📝 Reason: {reason}" if reason else "")
        )


    # === DELETE EVENT ===
    @admin_or_mod_check()
    @app_commands.describe(
        shortcode="Shortcode of the event to delete",
        reason="Reason for deleting (will be logged)"
    )
    @app_commands.command(name="delete", description="Delete an event.")
    async def delete_event(
        self, 
        interaction: discord.Interaction, 
        shortcode: str, 
        reason: str
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        with db_session() as session:
            event = events_crud.get_event_by_key(
                session=session,
                event_key=shortcode
            )
            if not event:
                await interaction.edit_original_response(content=f"❌ Event `{shortcode}` not found.", view=None)
                return

            if event.event_status in (EventStatus.visible, EventStatus.active):
                await interaction.edit_original_response(content="⚠️ Cannot delete an event that is active or visible. Put the event in draft first.", view=None)
                return
            
            # Extract now while session is open
            safe_event_name = event.event_name

        # Ask for confirmation
        confirmed = await confirm_action(
            interaction=interaction, 
            item_name=f"event `{shortcode}` ({safe_event_name})", 
            item_action="delete",
            reason="Removal"
        )
        if not confirmed:
            await interaction.edit_original_response(content="❌ Deletion cancelled or timed out.", view=None)
            return

        with db_session() as session:
            event = events_crud.delete_event(
                session,
                event_key=shortcode,
                performed_by=str(interaction.user.id),
                reason=reason
            )
            if not event:
                await interaction.edit_original_response(content="❌ Event deletion failed unexpectedly.", view=None)
                return

        await interaction.edit_original_response(content=f"✅ Event `{safe_event_name}` deleted.", view=None)
    

    # === LIST EVENTS ===
    @admin_or_mod_check()
    @app_commands.describe(
        tag="Filter by tag (optional)",
        event_status="Filter by status",
        moderator="Only show events created or edited by this moderator"
    )
    @app_commands.choices(
        event_status=[
            app_commands.Choice(name="Draft", value="draft"),
            app_commands.Choice(name="Visible", value="visible"),
            app_commands.Choice(name="Active", value="active"),
            app_commands.Choice(name="Archived", value="archived")
        ]
    )
    @app_commands.command(name="list", description="List all events with filters")
    async def list_events(
        self,
        interaction: Interaction,
        tag: Optional[str] = None,
        event_status: Optional[app_commands.Choice[str]] = None,
        moderator: Optional[discord.User] = None,
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        mod_by_discord_id = str(moderator.id) if moderator else None
        status_value = event_status.value if event_status else None
        
        with db_session() as session:
            events = events_crud.get_all_events(
                session,
                tag=tag,
                event_status = status_value,
                mod_by_discord_id=mod_by_discord_id
            )

            if not events:
                await interaction.followup.send("❌ No events found with the given filters.")
                return
    
            pages = []
            for i in range(0, len(events), EVENTS_PER_PAGE):
                chunk = events[i:i+EVENTS_PER_PAGE]
                description_text = f"🔍 Tag: `{tag}`\n" if tag else  ""
                embed = Embed(title=f"🗂️ Events List ({i+1}-{i+len(chunk)}/{len(events)})", description=description_text)
                for e in chunk:
                    updated_by = f"<@{e.modified_by}>" if e.modified_by else f"<@{e.created_by}>"
                    formatted_time = format_discord_timestamp(e.modified_at or e.created_at)
                    lines = [
                        f"**Shortcode:** `{e.event_key}` | **Name:** {e.event_name}",
                        f"👤 Last updated by: {updated_by}",
                        f":timer: On: {formatted_time}",
                        f"📌 Status: {e.event_status.value.capitalize()} | 📎 Embed: {'✅' if e.embed_message_discord_id else '❌'} | 🎭 Role: {'✅' if e.role_discord_id else '❌'}",
                    ]
                    embed.add_field(name="\n", value="\n".join(lines), inline=False)
                pages.append(embed)
    
            await paginate_embeds(interaction, pages)



    # === SHOW EVENT METADATA ===
    @admin_or_mod_check()
    @app_commands.command(name="show", description="Display event dashboard with a picker (no shortcode needed).")
    async def show_event(self, interaction: Interaction):
        """Opens an event picker; after selection, shows the Event Dashboard."""
        await interaction.response.defer(ephemeral=True)

        guild_id = interaction.guild.id if interaction.guild else None
        view = AdminEventPickerView(interaction, guild_id)
        await view.refresh()

        # Compact helper embed while picking
        pick_embed = Embed(
            title="🗓️ Event Browser",
            description=(
                "Use the **Status** filter and **Event** dropdown to open an event dashboard.\n"
                "• Max 25 options per page—use **Prev/Next** to navigate.\n"
                "• This panel is ephemeral (only you see it)."
            ),
            color=discord.Color.blurple()
        )

        await interaction.followup.send(embed=pick_embed, view=view)


    # === EVENT LOGS ===
    @admin_or_mod_check()
    @app_commands.describe(
        action="Filter by action type (create, edit, delete)",
        moderator="Filter by moderator (optional)"
    )
    @app_commands.command(name="logs", description="Show logs of event creation, edits, and deletion.")
    async def event_logs(
        self,
        interaction: discord.Interaction,
        action: Optional[str] = None,
        moderator: Optional[discord.User] = None,
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        with db_session() as session:
            logs = events_crud.get_event_logs(
                session=session,
                log_action=action,
                performed_by=str(moderator.id) if moderator else None
            )
    
            if not logs:
                await interaction.followup.send("❌ No logs found with those filters.")
                return
        
            pages = []
            for i in range(0, len(logs), LOGS_PER_PAGE):
                chunk = logs[i:i+LOGS_PER_PAGE]
                embed = discord.Embed(
                    title=f"📜 Event Logs ({i+1}-{i+len(chunk)}/{len(logs)})",
                    color=discord.Color.orange()
                )
                for log in chunk:
                    label = f"Event `{log.event_key}`" if log.event_key else "Deleted Event"
                    entry_str = format_log_entry(
                        log_action=log.log_action,
                        performed_by=log.performed_by,
                        performed_at=log.performed_at,
                        log_description=log.log_description,
                        label=label
                    )
                    embed.add_field(name="\n", value=entry_str, inline=False)
                pages.append(embed)
        
            await paginate_embeds(interaction, pages)


    # === SET EVENT STATUS ===
    @admin_or_mod_check()
    @app_commands.describe(
        shortcode="Shortcode of the event",
        event_status="New status: draft, visible, active, archived"
    )
    @app_commands.choices(
        event_status=[
            app_commands.Choice(name="Draft", value="draft"),
            app_commands.Choice(name="Visible", value="visible"),
            app_commands.Choice(name="Active", value="active"),
            app_commands.Choice(name="Archived", value="archived")
        ]
    )
    @app_commands.command(name="setstatus", description="Change the lifecycle status of an event.")
    async def set_event_status(
        self,
        interaction: discord.Interaction,
        shortcode: str,
        event_status: app_commands.Choice[str]
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)

        new_status = EventStatus(event_status.value)
        
        with db_session() as session:
            
            event = events_crud.get_event_by_key(
                session=session, 
                event_key=shortcode
            )
            if not event:                
                await interaction.followup.send(f"❌ Event `{shortcode}` not found.")
                return            

            old_status = event.event_status
            
            # Validation logic
            allowed_transitions = {
                EventStatus.draft: [EventStatus.visible],
                EventStatus.visible: [EventStatus.active, EventStatus.draft],
                EventStatus.active: [EventStatus.archived, EventStatus.visible, EventStatus.draft],
                EventStatus.archived: []
            }

            if new_status not in allowed_transitions[old_status]:
                await interaction.followup.send(
                    f"❌ Cannot move from {old_status.value} to {new_status.value}."
                )
                return
    
            if new_status == EventStatus.visible and not event.embed_message_discord_id:
                await interaction.followup.send("❌ You must define the embed message before making an event visible.")
                return

            status_update_data = {
                "event_status": new_status,
                "modified_by": str(interaction.user.id)
            }

            event = events_crud.set_event_status(
                session=session,
                event_key=shortcode,
                status_update_data=status_update_data
            )

            safe_event_name = event.event_name
            role_discord_id = event.role_discord_id

            # Announcement messages
            msg = None
            if old_status == EventStatus.draft and new_status == EventStatus.visible:
                msg = f"📢 The event **{safe_event_name}** is now visible to all members!"
            elif old_status == EventStatus.visible and new_status == EventStatus.active:
                msg = f"🎉 The event **{safe_event_name}** is now **active**!\nMembers can submit actions and browse the event rewards in the shop."
            elif old_status == EventStatus.active and new_status == EventStatus.archived:
    # Announcement messages
                msg = f"📢 **{safe_event_name}** is now **closed**. Thank you all for participating! 🎉\nLeaderboard and history remain accessible."
    
            if msg:
                await post_announcement_message(
                    interaction=interaction,
                    announcement_channel_id=EVENT_ANNOUNCEMENT_CHANNEL_ID,
                    msg=msg,
                    role_discord_id=role_discord_id
                )

        await interaction.followup.send(f"✅ Event `{safe_event_name} ({shortcode})` status changed to **{new_status.value}**.")


    # === REPORT COMMAND ===
    @admin_or_mod_check()
    @app_commands.describe(
        event="Filter by event (shortcode OR exact name). Leave empty for all.",
        date_from="Start date (YYYY-MM-DD, optional)",
        date_to="End date (YYYY-MM-DD, optional)",
        action_keys="Comma-separated action keys to include (optional)",
        only_with_url="Only include entries that have a URL (default: True)",
        only_active_actions="Show only ACTIVE actions (default: True)"   # <-- NEW
    )
    @app_commands.command(name="report", description="Report of completed user actions with filters (shareable list & CSV).")
    async def report_actions(
        self,
        interaction: Interaction,
        event: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        action_keys: Optional[str] = None,
        only_with_url: Optional[bool] = True,
        only_active_actions: Optional[bool] = True,   
    ):
        await interaction.response.defer(thinking=True, ephemeral=True)
    
        # Parse date filters safely
        df = safe_parse_date(date_from) if date_from else None
        dt = safe_parse_date(date_to) if date_to else None
        if date_from and not df:
            await interaction.followup.send("❌ Invalid `date_from`. Use YYYY-MM-DD.")
            return
        if date_to and not dt:
            await interaction.followup.send("❌ Invalid `date_to`. Use YYYY-MM-DD.")
            return
        df_iso, dt_iso = _iso_window(df, dt)
    
        # Parse action_keys
        ak_list: list[str] = []
        if action_keys:
            ak_list = [a.strip().lower() for a in action_keys.split(",") if a.strip()]
    
        # Query
        with db_session() as session:
            # Accept event key OR event name
            event_key = _resolve_event_key(session, event)
    
            rows = reports_crud.fetch_user_actions_report(
                session,
                event_key=event_key,
                date_from_iso=df_iso,
                date_to_iso=dt_iso,
                action_keys=ak_list or None,
                only_with_url=bool(only_with_url),
                only_active_actions=bool(only_active_actions), 
                limit=5000
            )
    
        if not rows:
            await interaction.followup.send("❌ No matching user actions found for those filters.")
            return
    
        # Build CSV (unchanged above) -> csv_bytes
        
        title_bits = []
        if event: title_bits.append(f"Event: **{event}**")
        if df: title_bits.append(f"From: `{df}`")
        if dt: title_bits.append(f"To: `{dt}`")
        if ak_list: title_bits.append(f"Actions: `{', '.join(ak_list)}`")
        if only_with_url: title_bits.append("Only URLs")
        if only_active_actions: title_bits.append("Active actions only")
            
        title = "📊 User Actions Report" + (" — " + " • ".join(title_bits) if title_bits else "")
        sio = StringIO()
        writer = csv.writer(sio)
        writer.writerow([
            "event_key","event_name","action_key","variant","created_at",
            "user_discord_id","display_name","url","numeric_value","text_value","boolean_value","date_value"
        ])
        for r in rows:
            writer.writerow([
                r.get("event_key",""),
                r.get("event_name",""),
                r.get("action_key",""),
                r.get("variant",""),
                r.get("created_at",""),
                r.get("user_discord_id",""),
                r.get("display_name",""),
                r.get("url",""),
                r.get("numeric_value",""),
                r.get("text_value",""),
                r.get("boolean_value",""),
                r.get("date_value",""),
            ])
        csv_bytes = sio.getvalue().encode("utf-8")
        # NEW: create the view with rows; it builds pages internally
        view = ReportResultsView(rows=rows, title=title, csv_bytes=csv_bytes, initial_group="action")
        
        # Send first page + controls
        await interaction.followup.send(embed=view.pages[0], view=view, ephemeral=True)
        
        

# === Setup Function ===
async def setup(bot):
    await bot.add_cog(AdminEventCommands(bot))