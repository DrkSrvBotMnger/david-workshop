# bot/ui/admin/reporting_views.py
from __future__ import annotations

import io
from typing import List, Optional, Sequence, Literal, Any

import discord
from discord import ui

from db.database import db_session  # your context manager
from bot.services.reporting_service import (
    build_event_options,
    build_action_event_options,
    get_points_leaderboard,
    get_prompts_leaderboard,
    get_actions_count_leaderboard,
    get_action_details,
    to_csv_bytes_from_points,
    to_csv_bytes_from_prompts,
    to_csv_bytes_from_action_counts,
    to_csv_bytes_from_action_details,
)
from bot.services.events_service import get_event_dto_by_id
from bot.config import CURRENCY

# ------------- Helpers -------------

def _render_with_limit(lines: list[str], hard_limit: int = 1900) -> str:
    """
    Join lines into a message that safely fits below Discord's 2000-char limit.
    Appends a truncated note when content is longer.
    """
    out = []
    used = 0
    for ln in lines:
        add = ln + "\n"
        if used + len(add) > hard_limit:
            remaining = max(0, len(lines) - len(out))
            out.append(f"_… truncated; {remaining} more lines. Use **Export CSV** or **Print in channel** for full data._")
            break
        out.append(ln)
        used += len(add)
    return "\n".join(out)


def _fmt_date(v) -> str:
    """Return YYYY-MM-DD whether v is datetime, date, or string-ish."""
    if v is None:
        return ""
    try:
        # datetime/date
        return v.strftime("%Y-%m-%d")  # type: ignore[attr-defined]
    except Exception:
        s = str(v)
        # common ISO or SQL text forms
        if "T" in s:
            return s.split("T", 1)[0]
        if " " in s:
            return s.split(" ", 1)[0]
        return s[:10]


def _paginate_lines(lines: list[str], hard_limit: int = 1900) -> list[str]:
    """
    Break lines into pages under ~2000 chars, add page footer.
    """
    pages, cur, cur_len = [], [], 0
    for ln in lines:
        add = ln + "\n"
        if cur and cur_len + len(add) > hard_limit:
            pages.append("\n".join(cur))
            cur, cur_len = [ln], len(add)
        else:
            cur.append(ln)
            cur_len += len(add)
    if cur:
        pages.append("\n".join(cur))
    if len(pages) > 1:
        pages = [p + f"\n_Page {i+1}/{len(pages)}_" for i, p in enumerate(pages)]
    return pages

def _join_and_truncate(items: list[str], sep: str = " , ", max_chars: int = 180) -> str:
    """Join items with a separator, capping total length, and add a (+N more) suffix if needed."""
    out, used = [], 0
    for i, s in enumerate(items):
        add = (sep if i else "") + s
        if used + len(add) > max_chars:
            remaining = len(items) - i
            if remaining > 0:
                out.append(f"{sep}(+{remaining} more)")
            break
        out.append(add if i else s)
        used += len(add)
    return "".join(out)

def _truncate(s: str, n: int = 48) -> str:
    return (s[: n - 1] + "…") if s and len(s) > n else (s or "")

def _chunk_lines(lines: List[str], max_chars: int = 1800) -> List[str]:
    chunks = []
    cur = ""
    for ln in lines:
        if len(cur) + len(ln) + 1 > max_chars:
            chunks.append(cur)
            cur = ""
        cur += (ln + "\n")
    if cur:
        chunks.append(cur)
    return chunks


# ------------- Main Entry View -------------

class AdminReportsHomeView(ui.View):
    def __init__(self, *, author_id: int, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.event_id: Optional[int] = None
        self.event_label: Optional[str] = None  # <- store pretty name
        self.report_type: Optional[Literal["leaderboards", "actions"]] = None

        self.event_select = EventSelect()
        self.add_item(self.event_select)
        self.add_item(ReportTypeSelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

class EventSelect(ui.Select):
    def __init__(self):
        with db_session() as session:
            ev_opts = build_event_options(session)

        if not ev_opts:
            super().__init__(
                placeholder="No events available",
                min_values=1, max_values=1,
                options=[discord.SelectOption(label="No events", value="-1")],
                disabled=True,
            )
            return

        # No defaults at construction time
        options = [
            discord.SelectOption(label=_truncate(opt.label, 90), value=str(opt.id))
            for opt in ev_opts[:25]
        ]
        super().__init__(placeholder="Select event…", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        home: AdminReportsHomeView = self.view  # type: ignore
        chosen = self.values[0]
        home.event_id = int(chosen)

        # Mark the chosen one as default so the collapsed select shows it
        for opt in self.options:
            opt.default = (opt.value == chosen)

        # Save pretty label for later printing
        sel = next((o for o in self.options if o.value == chosen), None)
        home.event_label = sel.label if sel else None

        await interaction.response.edit_message(view=home)

class ReportTypeSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Leaderboards", value="leaderboards", description=f"{CURRENCY.capitalize()} / Prompts / Action counts"),
            discord.SelectOption(label="Action List", value="actions", description="Detailed submissions"),
        ]
        super().__init__(placeholder="Select report type…", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        home: AdminReportsHomeView = self.view  # type: ignore[assignment]
        home.report_type = self.values[0]  # type: ignore
        if not home.event_id:
            await interaction.response.send_message("Please select an event first.", ephemeral=True)
            return
        if home.report_type == "leaderboards":
            await interaction.response.edit_message(view=LeaderboardsView(author_id=home.author_id, event_id=home.event_id))  # type: ignore[arg-type]

        else:
            await interaction.response.edit_message(view=ActionListView(author_id=home.author_id, event_id=home.event_id))  # type: ignore[arg-type]


# ------------- Leaderboards -------------

class LeaderboardsView(ui.View):
    def __init__(self, *, author_id: int, event_id: int, timeout: float = 360):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.event_id = event_id
        ev = get_event_dto_by_id(event_id)
        self.event_name = ev.event_name if ev else f"(Event {event_id})"
        self.kind_select = LeaderboardKindSelect()
        self.add_item(self.kind_select)
        self.action_event_select: Optional[ActionEventMultiSelect] = None

        self._last_payload: Optional[Any] = None  # cache rows for print/export
        self._last_kind: Optional[str] = None
        self._last_action_labels: list[str] = []

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    async def run_and_render(self, interaction: discord.Interaction):
        kind = self.kind_select.values[0]
        self._last_kind = kind

        if kind == "points":
            with db_session() as session:
                rows = get_points_leaderboard(session, self.event_id)
            self._last_payload = rows

            lines = [f"**Leaderboard – {CURRENCY.capitalize()} - {self.event_name}**"]
            for i, r in enumerate(rows, 1):
                lines.append(f"{i:>2}. <@{r.user_discord_id}> — {r.points} {CURRENCY}")
            content = "\n".join(lines) if lines else "No data."

            # action-event select not needed
            if self.action_event_select:
                self.remove_item(self.action_event_select)
                self.action_event_select = None

            self._refresh_export_buttons()
            await interaction.response.edit_message(content=content, view=self)

        elif kind == "prompts":
            with db_session() as session:
                rows = get_prompts_leaderboard(session, self.event_id)
            self._last_payload = rows

            lines = [f"**Leaderboard – Prompts - {self.event_name}**"]
            for i, r in enumerate(rows, 1):
                lines.append(f"{i:>2}. <@{r.user_discord_id}> — unique {r.unique_prompts} / total {r.total_prompts}")
            content = "\n".join(lines) if lines else "No data."

            if self.action_event_select:
                self.remove_item(self.action_event_select)
                self.action_event_select = None

            self._refresh_export_buttons()
            await interaction.response.edit_message(content=content, view=self)

        else:  # kind == 'actions_count'
            # Need action_event multi-select
            if not self.action_event_select:
                self.action_event_select = ActionEventMultiSelect(self.event_id, placeholder="Pick one or more ActionEvents…")
                self.add_item(self.action_event_select)
    
            # ✅ make sure Run / Print / Export are present the first time too
            self._refresh_export_buttons()
    
            await interaction.response.edit_message(
                content="Select ActionEvent(s) then press **Run**.",
                view=self
            )

    def _refresh_export_buttons(self):
        # reset buttons
        for child in list(self.children):
            if isinstance(child, (ExportCsvButton, PrintChannelButton, RunButton)):
                self.remove_item(child)
        self.add_item(RunButton(self))
        self.add_item(PrintChannelButton(self))
        self.add_item(ExportCsvButton(self))

class LeaderboardKindSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=f"Users by {CURRENCY}", value="points"),
            discord.SelectOption(label="Users by prompts (prompt events)", value="prompts"),
            discord.SelectOption(label="Users by # of actions (select ActionEvent)", value="actions_count"),
        ]
        super().__init__(placeholder="Select leaderboard kind…", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        view: LeaderboardsView = self.view  # type: ignore[assignment]
        await view.run_and_render(interaction)

class ActionEventMultiSelect(ui.Select):
    def __init__(self, event_id: int, placeholder: str = "Select ActionEvents…"):
        with db_session() as session:
            opts = build_action_event_options(session, event_id)
        options = [discord.SelectOption(label=_truncate(o.label, 90), value=str(o.id)) for o in opts][:25]
        super().__init__(placeholder=placeholder, min_values=1, max_values=min(25, len(options)) or 1, options=options)

    async def callback(self, interaction: discord.Interaction):
        # No auto-run; user must click Run.
        await interaction.response.defer()  # noop

class RunButton(ui.Button):
    def __init__(self, parent_view: LeaderboardsView):
        super().__init__(label="Run", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        pv = self.parent_view
        if isinstance(pv, LeaderboardsView) and pv._last_kind == "actions_count":
            sel: ActionEventMultiSelect = pv.action_event_select  # type: ignore
            if not sel or not sel.values:
                await interaction.response.send_message("Pick at least one ActionEvent.", ephemeral=True)
                return

            # Collect nice labels for the header
            selected_values = set(sel.values)
            labels = [opt.label for opt in sel.options if opt.value in selected_values]
            pv._last_action_labels = labels

            ae_ids = [int(v) for v in sel.values]
            with db_session() as session:
                rows = get_actions_count_leaderboard(session, pv.event_id, ae_ids)
            pv._last_payload = rows

            title = getattr(pv, "event_label", None) or f"Event {pv.event_id}"
            lines = [f"**Leaderboard – # of Actions - {pv.event_name}**"]

            if labels:
                lines.append(f"*Actions:* {_join_and_truncate(labels)}")

            for i, r in enumerate(rows, 1):
                lines.append(f"{i:>2}. <@{r.user_discord_id}> — {r.count}")

            content = _render_with_limit(lines) if lines else "No data."
            pv._refresh_export_buttons()
            await interaction.response.edit_message(content=content, view=pv)
        else:
            await interaction.response.send_message("Select a leaderboard kind first.", ephemeral=True)

class PrintChannelButton(ui.Button):
    def __init__(self, parent_view: LeaderboardsView):
        super().__init__(label="Print in channel", style=discord.ButtonStyle.secondary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        payload = self.parent_view._last_payload
        if payload is None:
            await interaction.response.send_message("Run a report first.", ephemeral=True)
            return

        title = getattr(self.parent_view, "event_label", None) or f"Event {self.parent_view.event_id}"
        lines: list[str] = []

        if self.parent_view._last_kind == "points":
            lines.append(f"**Leaderboard – {CURRENCY.capitalize()} - {self.parent_view.event_name}**")
            for i, r in enumerate(payload, 1):
                lines.append(f"{i:>2}. <@{r.user_discord_id}> — {r.points} {CURRENCY}")

        elif self.parent_view._last_kind == "prompts":
            lines.append(f"**Leaderboard – Prompts - {self.parent_view.event_name}**")
            for i, r in enumerate(payload, 1):
                lines.append(f"{i:>2}. <@{r.user_discord_id}> — unique {r.unique_prompts} / total {r.total_prompts}")

        else:  # actions_count
            lines.append(f"**Leaderboard – # of Actions - {self.parent_view.event_name}**")
            labels = getattr(self.parent_view, "_last_action_labels", []) or []
            if labels:
                lines.append(f"*Actions:* {_join_and_truncate(labels)}")
            for i, r in enumerate(payload, 1):
                lines.append(f"{i:>2}. <@{r.user_discord_id}> — {r.count}")

        chunks = _chunk_lines(lines)
        await interaction.response.defer()
        for chunk in chunks:
            msg = await interaction.channel.send(chunk, allowed_mentions=discord.AllowedMentions.none())
            await msg.edit(suppress=True)

class ExportCsvButton(ui.Button):
    def __init__(self, parent_view: LeaderboardsView):
        super().__init__(label="Export CSV", style=discord.ButtonStyle.success)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        payload = self.parent_view._last_payload
        if payload is None:
            await interaction.response.send_message("Run a report first.", ephemeral=True)
            return

        if self.parent_view._last_kind == "points":
            data = to_csv_bytes_from_points(payload)
            name = "leaderboard_points.csv"
        elif self.parent_view._last_kind == "prompts":
            data = to_csv_bytes_from_prompts(payload)
            name = "leaderboard_prompts.csv"
        else:
            data = to_csv_bytes_from_action_counts(payload)
            name = "leaderboard_actions.csv"

        fp = io.BytesIO(data)
        fp.seek(0)
        await interaction.response.send_message(file=discord.File(fp, filename=name), ephemeral=True)


# ------------- Action List -------------

class ActionListView(ui.View):
    def __init__(self, *, author_id: int, event_id: int, timeout: float = 360):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.event_id = event_id
        ev = get_event_dto_by_id(event_id)
        self.event_label = ev.event_name if ev else f"(Event {event_id})"

        self._sort_value: str = "created_at:desc"

        self.action_select = ActionEventMultiSelect(event_id, placeholder="Pick one or more ActionEvents…")
        self.add_item(self.action_select)

        self.sort_select = SortSelect()
        self.add_item(self.sort_select)

        self.add_item(DateInputButton())

        self._date_iso: Optional[str] = None
        self._rows_cache = None

        self.add_item(ActionRunButton(self))
        self.add_item(ActionPrintButton(self))
        self.add_item(ActionExportButton(self))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    async def set_date(self, date_iso: Optional[str], interaction: discord.Interaction):
        self._date_iso = date_iso
        await interaction.response.send_message(
            f"✅ Date filter set to **{date_iso or 'All event'}**. Press **Run** to refresh.",
            ephemeral=True
        )

class SortSelect(ui.Select):
    def __init__(self, default_value: str = "created_at:desc"):
        options = [
            discord.SelectOption(label="Sort by date (desc)", value="created_at:desc", default=True),
            discord.SelectOption(label="Sort by date (asc)", value="created_at:asc"),
            discord.SelectOption(label="Sort by URL (asc)", value="url:asc"),
            discord.SelectOption(label="Sort by number (desc)", value="numeric:desc"),
            discord.SelectOption(label="Sort by number (asc)", value="numeric:asc"),
            discord.SelectOption(label="Sort by text (asc)", value="text:asc"),
            discord.SelectOption(label="Sort by bool (asc)", value="bool:asc"),
            discord.SelectOption(label="Sort by date_value (asc)", value="date:asc"),
        ]
        super().__init__(placeholder="Pick sorting…", min_values=1, max_values=1, options=options)
        for opt in self.options:
            opt.default = (opt.value == default_value)


    async def callback(self, interaction: discord.Interaction):
        # Mark the chosen option as default so the closed dropdown shows it
        chosen = self.values[0]
        for opt in self.options:
            opt.default = (opt.value == chosen)
            
        # Persist on the owning view
        view: ActionListView = self.view  # type: ignore
        view._sort_value = chosen

        # Re-render the message so the visual selection updates
        await interaction.response.edit_message(view=view)

class DateInputModal(ui.Modal, title="Filter by Civic Day"):
    date = ui.TextInput(label="Date (YYYY-MM-DD) or leave blank", required=False, max_length=10, placeholder="2025-08-20")

    def __init__(self, parent_view: ActionListView):
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        v = str(self.date.value).strip()
        await self.parent_view.set_date(v if v else None, interaction)

class DateInputButton(ui.Button):
    def __init__(self):
        super().__init__(label="Pick date", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        # Pass the actual ActionListView instance (self.view), not interaction.view
        await interaction.response.send_modal(DateInputModal(self.view))  # type: ignore

class ActionRunButton(ui.Button):
    def __init__(self, parent_view: ActionListView):
        super().__init__(label="Run", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        sel = self.parent_view.action_select
        if not sel.values:
            await interaction.response.send_message("Pick at least one ActionEvent.", ephemeral=True)
            return

        ae_ids = [int(v) for v in sel.values]

        sortv = self.parent_view._sort_value or "created_at:desc"
        field, direction = sortv.split(":")
        asc = (direction == "asc")

        with db_session() as session:
            rows = get_action_details(
                session, self.parent_view.event_id, ae_ids,
                self.parent_view._date_iso, field, asc
            )
        self.parent_view._rows_cache = rows

        used = {
            "prompts_count": any(r.prompts_count for r in rows),
            "url_value": any(r.url_value for r in rows),
            "numeric_value": any(r.numeric_value is not None for r in rows),
            "text_value": any(r.text_value for r in rows),
            "boolean_value": any(r.boolean_value is not None for r in rows),
            "date_value": any(r.date_value for r in rows),
        }

        headers = ["date","name"]
        for k, title in [
            ("prompts_count", "#p"),
            ("url_value", "url"),
            ("numeric_value", "num"),
            ("text_value", "text"),
            ("boolean_value", "bool"),
            ("date_value", "dval"),
        ]:
            if used[k]:
                headers.append(title)

        lines = ["**Action List Report**", "`" + " | ".join(headers) + "`"]
        for r in rows:
            vals = [_fmt_date(r.created_at),_truncate(r.display_name, 28)]
            if used["prompts_count"]: vals.append(str(r.prompts_count))
            if used["url_value"]:     vals.append(_truncate(r.url_value, 32) if r.url_value else "")
            if used["numeric_value"]: vals.append("" if r.numeric_value is None else str(r.numeric_value))
            if used["text_value"]:    vals.append(_truncate(r.text_value, 32) if r.text_value else "")
            if used["boolean_value"]: vals.append("" if r.boolean_value is None else ("true" if r.boolean_value else "false"))
            if used["date_value"]:    vals.append(_fmt_date(r.date_value))
            lines.append("`" + " | ".join(vals) + "`")

        # Keep preview under 2k, with a hint
        content = _render_with_limit(lines)
        await interaction.response.edit_message(content=content, view=self.parent_view)

class ActionPrintButton(ui.Button):
    def __init__(self, parent_view: ActionListView):
        super().__init__(label="Print in channel", style=discord.ButtonStyle.secondary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        rows = self.parent_view._rows_cache
        if not rows:
            await interaction.response.send_message("Run a report first.", ephemeral=True)
            return

        used = {
            "prompts_count": any(r.prompts_count for r in rows),
            "url_value": any(r.url_value for r in rows),
            "numeric_value": any(r.numeric_value is not None for r in rows),
            "text_value": any(r.text_value for r in rows),
            "boolean_value": any(r.boolean_value is not None for r in rows),
            "date_value": any(r.date_value for r in rows),
        }
        headers = ["date","name"]
        for k, title in [
            ("prompts_count", "# prompts"),
            ("url_value", "url"),
            ("numeric_value", "num"),
            ("text_value", "text"),
            ("boolean_value", "bool"),
            ("date_value", "dval"),
        ]:
            if used[k]:
                headers.append(title)

        lines = [" | ".join(headers) ]
        for r in rows:
            vals = [_fmt_date(r.created_at),"<@"+r.user_discord_id+">"]
            if used["prompts_count"]: vals.append(str(r.prompts_count))
            if used["url_value"]:     vals.append(r.url_value if r.url_value else "")
            if used["numeric_value"]: vals.append("" if r.numeric_value is None else str(r.numeric_value))
            if used["text_value"]:    vals.append(_truncate(r.text_value, 64) if r.text_value else "")
            if used["boolean_value"]: vals.append("" if r.boolean_value is None else ("true" if r.boolean_value else "false"))
            if used["date_value"]:    vals.append(_fmt_date(r.date_value))
            lines.append(" | ".join(vals))

        pages = _paginate_lines(lines)
        title = self.parent_view.event_label or f"Event {self.parent_view.event_id}"
        pages[0] = f"**Action List Report — {title}**\n" + pages[0]

        await interaction.response.defer()
        msg = await interaction.channel.send(
            pages[0],
            view=PaginatedMessageView(pages=pages, author_id=interaction.user.id),
            allowed_mentions=discord.AllowedMentions.none(),
        )  # type: ignore
        await msg.edit(suppress=True)

class ActionExportButton(ui.Button):
    def __init__(self, parent_view: ActionListView):
        super().__init__(label="Export CSV", style=discord.ButtonStyle.success)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        rows = self.parent_view._rows_cache
        if not rows:
            await interaction.response.send_message("Run a report first.", ephemeral=True)
            return
        data = to_csv_bytes_from_action_details(rows)
        fp = io.BytesIO(data); fp.seek(0)
        await interaction.response.send_message(file=discord.File(fp, filename="actions_report.csv"), ephemeral=True)

class PaginatedMessageView(ui.View):
    def __init__(self, *, pages: list[str], author_id: int, timeout: float = 600):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.pages = pages
        self.index = 0
        self.add_item(PagerPrevButton(self))
        self.add_item(PagerNextButton(self))
        self.add_item(PagerCloseButton(self))
        self._sync()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    def _sync(self):
        for c in self.children:
            if isinstance(c, PagerPrevButton):
                c.disabled = (self.index <= 0)
            if isinstance(c, PagerNextButton):
                c.disabled = (self.index >= len(self.pages) - 1)

class PagerPrevButton(ui.Button):
    def __init__(self, owner: PaginatedMessageView):
        super().__init__(label="Prev", style=discord.ButtonStyle.secondary)
        self.owner = owner
    async def callback(self, interaction: discord.Interaction):
        self.owner.index = max(0, self.owner.index - 1)
        self.owner._sync()
        await interaction.response.edit_message(content=self.owner.pages[self.owner.index], view=self.owner, allowed_mentions=discord.AllowedMentions.none())
        # Immediately suppress any new embed previews
        await interaction.message.edit(suppress=True)

class PagerNextButton(ui.Button):
    def __init__(self, owner: PaginatedMessageView):
        super().__init__(label="Next", style=discord.ButtonStyle.secondary)
        self.owner = owner
    async def callback(self, interaction: discord.Interaction):
        self.owner.index = min(len(self.owner.pages) - 1, self.owner.index + 1)
        self.owner._sync()
        await interaction.response.edit_message(content=self.owner.pages[self.owner.index], view=self.owner, allowed_mentions=discord.AllowedMentions.none())
        # Immediately suppress any new embed previews
        await interaction.message.edit(suppress=True)

class PagerCloseButton(ui.Button):
    def __init__(self, owner: PaginatedMessageView):
        super().__init__(label="Close", style=discord.ButtonStyle.danger)
        self.owner = owner
    async def callback(self, interaction: discord.Interaction):
        for c in self.owner.children:
            if isinstance(c, ui.Button):
                c.disabled = True
        await interaction.response.edit_message(view=self.owner)
        
