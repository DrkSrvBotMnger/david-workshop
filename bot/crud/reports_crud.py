# bot/crud/reports_crud.py
from typing import Optional, Sequence
from sqlalchemy import and_
from sqlalchemy.orm import Session
from db.schema import UserAction, ActionEvent, Action, Event, User

def fetch_user_actions_report(
    session: Session,
    *,
    event_key: Optional[str] = None,
    date_from_iso: Optional[str] = None,
    date_to_iso: Optional[str] = None,
    action_keys: Optional[Sequence[str]] = None,
    only_with_url: bool = False,
    only_active_actions: bool = True,   # <-- NEW (default = True)
    limit: int = 5000
) -> list[dict]:

    q = (
        session.query(
            Event.event_key,
            Event.event_name,
            Action.action_key,
            ActionEvent.variant,
            UserAction.created_at,
            User.id.label("user_id"),
            User.user_discord_id,
            User.display_name,
            UserAction.url.label("url"),      # rename if your column differs
            UserAction.numeric_value,
            UserAction.text_value,
            UserAction.boolean_value,
            UserAction.date_value,
        )
        .join(ActionEvent, ActionEvent.id == UserAction.action_event_id)
        .join(Event, Event.id == ActionEvent.event_id)
        .outerjoin(Action, Action.id == ActionEvent.action_id)  # keep OUTER to allow historical rows
        .join(User, User.id == UserAction.user_id)
    )

    # NEW: filter to active actions by default (belt + suspenders)
    if only_active_actions:
        q = q.filter(and_(Action.is_active.is_(True), Action.deactivated_at.is_(None)))

    if event_key:
        q = q.filter(Event.event_key == event_key)
    if date_from_iso:
        q = q.filter(UserAction.created_at >= date_from_iso)
    if date_to_iso:
        q = q.filter(UserAction.created_at <= date_to_iso)
    if action_keys:
        aks = [a.strip().lower() for a in action_keys if a and a.strip()]
        if aks:
            q = q.filter(Action.action_key.in_(aks))
    if only_with_url:
        q = q.filter(UserAction.url.isnot(None)).filter(UserAction.url != "")

    rows = q.order_by(UserAction.created_at.desc()).limit(limit).all()

    return [{
        "event_key": r.event_key,
        "event_name": r.event_name,
        "action_key": r.action_key,
        "variant": r.variant,
        "created_at": r.created_at,
        "user_id": r.user_id,
        "user_discord_id": r.user_discord_id,
        "display_name": r.display_name,
        "url": r.url,
        "numeric_value": r.numeric_value,
        "text_value": r.text_value,
        "boolean_value": r.boolean_value,
        "date_value": r.date_value,
    } for r in rows]
