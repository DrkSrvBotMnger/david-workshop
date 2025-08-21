# bot/services/reporting_service.py
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, Dict, Any

from sqlalchemy.orm import Session

from bot.crud.reporting_crud import (
    list_events_for_admin,
    list_action_events_for_event,
    leaderboard_points_by_event,
    leaderboard_prompts_by_event,
    leaderboard_actions_by_action_events,
    list_actions_for_action_events,
)

# ---------- DTOs / VMs ----------

@dataclass
class EventOption:
    id: int
    label: str  # e.g., "[ACTIVE] Darklina Week (drkwk2508)"
    is_active: bool

@dataclass
class ActionEventOption:
    id: int
    label: str  # e.g., "Submit a fic (default)"
    action_description: str
    variant: str

@dataclass
class PointsRow:
    user_discord_id: str
    display_name: str
    points: int

@dataclass
class PromptsRow:
    user_discord_id: str
    display_name: str
    total_prompts: int
    unique_prompts: int

@dataclass
class ActionsCountRow:
    user_discord_id: str
    display_name: str
    count: int

@dataclass
class ActionDetailRow:
    display_name: str
    user_discord_id: str
    created_at: str
    url_value: Optional[str]
    numeric_value: Optional[int]
    text_value: Optional[str]
    boolean_value: Optional[bool]
    date_value: Optional[str]
    prompts_count: int


# ---------- Facade ----------

def build_event_options(session: Session) -> List[EventOption]:
    res = []
    for e in list_events_for_admin(session):
        raw = getattr(e.event_status, "value", e.event_status)  # enum or str
        status = (raw or "").lower()
        tag = (status or "unknown").upper()
        res.append(
            EventOption(
                id=e.id,
                label=f"[{tag}] {e.event_name} ({e.event_key})",
                is_active=(status == "active"),
            )
        )
    return res

def build_action_event_options(session: Session, event_id: int) -> List[ActionEventOption]:
    res = []
    for ae, a in list_action_events_for_event(session, event_id):
        res.append(ActionEventOption(id=ae.id, label=f"{a.action_description} ({ae.variant})", action_description=a.action_description, variant=ae.variant))
    return res


# ---------- Leaderboards ----------

def get_points_leaderboard(session: Session, event_id: int) -> List[PointsRow]:
    rows = leaderboard_points_by_event(session, event_id)
    return [
        PointsRow(
            user_discord_id=r["user_discord_id"],
            display_name=r["display_name"],
            points=int(r["points"]),
        )
        for r in rows
    ]


def get_prompts_leaderboard(session: Session, event_id: int) -> List[PromptsRow]:
    rows = leaderboard_prompts_by_event(session, event_id)
    return [
        PromptsRow(
            user_discord_id=r["user_discord_id"],
            display_name=r["display_name"],
            total_prompts=int(r["total_prompts"]),
            unique_prompts=int(r["unique_prompts"]),
        )
        for r in rows
    ]


def get_actions_count_leaderboard(session: Session, event_id: int, ae_ids: Sequence[int]) -> List[ActionsCountRow]:
    rows = leaderboard_actions_by_action_events(session, event_id, ae_ids)
    return [
        ActionsCountRow(
            user_discord_id=r["user_discord_id"],
            display_name=r["display_name"],
            count=int(r["count"]),
        )
        for r in rows
    ]


# ---------- Actions List ----------

def get_action_details(
    session: Session,
    event_id: int,
    ae_ids: Sequence[int],
    date_iso: Optional[str],
    order_field: str,
    ascending: bool,
) -> List[ActionDetailRow]:
    rows = list_actions_for_action_events(session, event_id, ae_ids, date_iso, order_field, ascending)
    return [
        ActionDetailRow(
            display_name=r["display_name"],
            user_discord_id=r["user_discord_id"],
            created_at=r["created_at"],
            url_value=r["url_value"],
            numeric_value=r["numeric_value"],
            text_value=r["text_value"],
            boolean_value=r["boolean_value"],
            date_value=r["date_value"],
            prompts_count=int(r.get("prompts_count", 0)),
        )
        for r in rows
    ]


# ---------- CSV Helpers ----------

def to_csv_bytes_from_points(rows: List[PointsRow]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["display_name", "user_discord_id", "points"])
    for r in rows:
        w.writerow([r.display_name, r.user_discord_id, r.points])
    return buf.getvalue().encode("utf-8")


def to_csv_bytes_from_prompts(rows: List[PromptsRow]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["display_name", "user_discord_id", "total_prompts", "unique_prompts"])
    for r in rows:
        w.writerow([r.display_name, r.user_discord_id, r.total_prompts, r.unique_prompts])
    return buf.getvalue().encode("utf-8")


def to_csv_bytes_from_action_counts(rows: List[ActionsCountRow]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["display_name", "user_discord_id", "count"])
    for r in rows:
        w.writerow([r.display_name, r.user_discord_id, r.count])
    return buf.getvalue().encode("utf-8")


def to_csv_bytes_from_action_details(rows: List[ActionDetailRow]) -> bytes:
    # Dynamic columns: include only used value columns
    used = {
        "url_value": any(r.url_value for r in rows),
        "numeric_value": any(r.numeric_value is not None for r in rows),
        "text_value": any(r.text_value for r in rows),
        "boolean_value": any(r.boolean_value is not None for r in rows),
        "date_value": any(r.date_value for r in rows),
        "prompts_count": any(r.prompts_count for r in rows),
    }
    headers = ["created_at", "display_name", "user_discord_id"]
    for k in ["url_value", "numeric_value", "text_value", "boolean_value", "date_value", "prompts_count"]:
        if used[k]:
            headers.append(k)

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        row = [r.created_at, r.display_name, r.user_discord_id]
        if used["url_value"]: row.append(r.url_value or "")
        if used["numeric_value"]: row.append("" if r.numeric_value is None else r.numeric_value)
        if used["text_value"]: row.append(r.text_value or "")
        if used["boolean_value"]: row.append("" if r.boolean_value is None else ("true" if r.boolean_value else "false"))
        if used["date_value"]: row.append(r.date_value or "")
        if used["prompts_count"]: row.append(r.prompts_count)
        w.writerow(row)
    return buf.getvalue().encode("utf-8")
