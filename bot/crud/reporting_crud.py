# bot/crud/reporting_crud.py
from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple, Dict, Any
from sqlalchemy import func, case, and_, or_, literal
from sqlalchemy.orm import Session

from db.schema import (
    User, Event, Action, ActionEvent, UserAction, UserEventData,
    EventPrompt, UserActionPrompt, EventTrigger, UserEventTriggerLog
)

# ---------- Lookups ----------

def list_events_for_admin(session: Session) -> List[Event]:
    """
    Return events ordered by status then priority desc then start_date desc.
    Keep it light; the admin view will show all.
    """
    # event_status is Enum; order 'active', 'visible', 'draft', 'archived' roughly
    # Simple order by priority desc and start_date desc for now.
    return (
        session.query(Event)
        .order_by(Event.priority.desc(), Event.start_date.desc())
        .all()
    )

def list_action_events_for_event(session: Session, event_id: int) -> List[Tuple[ActionEvent, Action]]:
    """
    Return (ActionEvent, Action) for a given event, ordered by action_key then variant.
    """
    rows = (
        session.query(ActionEvent, Action)
        .join(Action, ActionEvent.action_id == Action.id)
        .filter(ActionEvent.event_id == event_id)
        .order_by(Action.action_key.asc(), ActionEvent.variant.asc())
        .all()
    )
    return [(ae, a) for (ae, a) in rows]

# ---------- Leaderboards ----------

def leaderboard_points_by_event(session, event_id: int) -> list[dict]:
    q = (
        session.query(
            User.id.label("user_id"),
            User.user_discord_id.label("user_discord_id"),
            User.display_name.label("display_name"),
            UserEventData.points_earned.label("points"),
        )
        .join(UserEventData, UserEventData.user_id == User.id)
        .filter(UserEventData.event_id == event_id)
        .order_by(UserEventData.points_earned.desc(), User.display_name.asc())
    )
    return [dict(r._asdict()) for r in q.all()]

def leaderboard_prompts_by_event(session: Session, event_id: int) -> List[Dict[str, Any]]:
    """
    For 'prompt' events: count total selected prompts (duplicates allowed)
    and unique prompts per user.
    Returns rows: { user_id, user_discord_id, display_name, total_prompts, unique_prompts }
    """
    # Join UserActionPrompt -> UserAction -> ActionEvent (filter event)
    base = (
        session.query(
            User.id.label("user_id"),
            User.user_discord_id.label("user_discord_id"),
            User.display_name.label("display_name"),
            UserActionPrompt.event_prompt_id.label("pid")
        )
        .join(UserAction, UserActionPrompt.user_action_id == UserAction.id)
        .join(ActionEvent, UserAction.action_event_id == ActionEvent.id)
        .join(User, UserAction.user_id == User.id)
        .filter(ActionEvent.event_id == event_id)
    ).subquery()

    # total prompts
    q_total = (
        session.query(
            base.c.user_id,
            func.count().label("total_prompts")
        ).group_by(base.c.user_id)
    )
    totals = {r.user_id: r.total_prompts for r in q_total.all()}

    # unique prompts
    q_unique = (
        session.query(
            base.c.user_id,
            func.count(func.distinct(base.c.pid)).label("unique_prompts")
        ).group_by(base.c.user_id)
    )
    uniques = {r.user_id: r.unique_prompts for r in q_unique.all()}

    # Names
    users = session.query(User).filter(User.id.in_(set(totals) | set(uniques))).all()
    by_id = {u.id: u for u in users}

    rows = []
    for uid in set(totals) | set(uniques):
        u = by_id[uid]
        rows.append({
            "user_id": uid,
            "user_discord_id": u.user_discord_id,
            "display_name": u.display_name,
            "total_prompts": int(totals.get(uid, 0)),
            "unique_prompts": int(uniques.get(uid, 0))
        })

    return sorted(rows, key=lambda x: (-x["unique_prompts"], -x["total_prompts"], x["display_name"].casefold()))


def leaderboard_actions_by_action_events(
    session: Session, event_id: int, action_event_ids: Sequence[int]
) -> List[Dict[str, Any]]:
    """
    Count # of user actions restricted to selected ActionEvent ids in the event.
    Returns rows: { user_id, user_discord_id, display_name, count }
    """
    if not action_event_ids:
        return []

    q = (
        session.query(
            User.id.label("user_id"),
            User.user_discord_id.label("user_discord_id"),
            User.display_name.label("display_name"),
            func.count(UserAction.id).label("count"),
        )
        .join(UserAction, UserAction.user_id == User.id)
        .filter(UserAction.action_event_id.in_(list(action_event_ids)))
    )

    # (Optional) extra safety filter on event_id from ActionEvent
    q = q.join(ActionEvent, UserAction.action_event_id == ActionEvent.id).filter(ActionEvent.event_id == event_id)

    q = q.group_by(User.id, User.user_discord_id, User.display_name).order_by(
        func.count(UserAction.id).desc(), User.display_name.asc()
    )

    return [dict(r._asdict()) for r in q.all()]


# ---------- Action List ----------

def list_actions_for_action_events(
    session: Session,
    event_id: int,
    action_event_ids: Sequence[int],
    date_iso: Optional[str],  # 'YYYY-MM-DD' to consider that whole civic day
    order_field: str,         # 'created_at'|'url'|'numeric'|'text'|'bool'|'date'
    ascending: bool
) -> List[Dict[str, Any]]:
    """
    Return action rows for selected action events + optional civic date filter.
    Dynamically include only used value columns.
    """
    if not action_event_ids:
        return []

    q = (
        session.query(
            UserAction.id.label("id"),
            User.display_name.label("display_name"),
            User.user_discord_id.label("user_discord_id"),
            UserAction.created_at.label("created_at"),
            UserAction.url_value.label("url_value"),
            UserAction.numeric_value.label("numeric_value"),
            UserAction.text_value.label("text_value"),
            UserAction.boolean_value.label("boolean_value"),
            UserAction.date_value.label("date_value"),
            UserAction.action_event_id.label("action_event_id"),
        )
        .join(User, User.id == UserAction.user_id)
        .filter(UserAction.action_event_id.in_(list(action_event_ids)))
    )

    if date_iso:
        # civic day -> filter from 'YYYY-MM-DDT00:00:00' inclusive to next day exclusive;
        since = f"{date_iso}T00:00:00"
        until = f"{date_iso}T23:59:59"
        q = q.filter(and_(UserAction.created_at >= since, UserAction.created_at <= until))

    # sorting
    col_map = {
        "created_at": UserAction.created_at,
        "url": UserAction.url_value,
        "numeric": UserAction.numeric_value,
        "text": UserAction.text_value,
        "bool": UserAction.boolean_value,
        "date": UserAction.date_value,
    }
    sort_col = col_map.get(order_field, UserAction.created_at)
    q = q.order_by(sort_col.asc() if ascending else sort_col.desc())

    rows = [dict(r._asdict()) for r in q.all()]

    # add prompts_count per action if any
    if rows:
        ids = [r["id"] for r in rows]
        q_prompts = (
            session.query(
                UserActionPrompt.user_action_id,
                func.count(UserActionPrompt.id)
            )
            .filter(UserActionPrompt.user_action_id.in_(ids))
            .group_by(UserActionPrompt.user_action_id)
        )
        counts = {k: v for k, v in q_prompts.all()}
        for r in rows:
            r["prompts_count"] = int(counts.get(r["id"], 0))

    return rows
