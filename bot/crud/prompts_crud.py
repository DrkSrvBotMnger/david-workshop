# bot/crud/prompts_crud.py
from typing import Iterable, Optional, Sequence
from sqlalchemy.orm import Session
from sqlalchemy import func
from db.schema import EventPrompt, UserActionPrompt, ActionEvent, UserAction

# ---------- EVENT PROMPTS ----------

def get_prompts_for_event(
    session: Session,
    event_id: int,
    group: Optional[str] = None,
    active_only: bool = True,
) -> list[EventPrompt]:
    """
    Get all prompts for an event, optionally filtered by group.
    """
    q = session.query(EventPrompt).filter(EventPrompt.event_id == event_id)
    if group:
        q = q.filter(EventPrompt.group == group)
    if active_only:
        q = q.filter(EventPrompt.is_active.is_(True))
    return q.order_by(
        func.coalesce(EventPrompt.group, ""), func.coalesce(EventPrompt.day_index, 0), func.lower(EventPrompt.label)
    ).all()

def get_prompt_by_code_and_event(
    session: Session,
    code: str,
    event_id: int
) -> Optional[EventPrompt]:
    return session.query(EventPrompt).filter(EventPrompt.code == code, EventPrompt.event_id == event_id).first()

def upsert_prompts_bulk(
    session: Session,
    *,
    event_id: int,
    group: Optional[str],
    labels_in_order: Sequence[str],
    created_by: str,
    created_at: str,
) -> list[EventPrompt]:
    """
    Idempotent bulk load: for i, label in enumerate(labels, 1)
      - code pattern: "<group>-<i:02d>" if group else f"d{i:02d}"
      - if exists for (event_id, code): update label + is_active=True
      - if not: create
    """
    results: list[EventPrompt] = []
    for i, label in enumerate(labels_in_order, start=1):
        if not label or not str(label).strip():
            continue
        day = i
        code = f"{group}-{i:02d}" if group else f"d{i:02d}"

        row = (
            session.query(EventPrompt)
            .filter(EventPrompt.event_id == event_id, EventPrompt.code == code)
            .first()
        )
        if row:
            row.label = str(label).strip()
            row.day_index = day
            row.group = group
            row.is_active = True
            row.modified_by = created_by
            row.modified_at = created_at
        else:
            row = EventPrompt(
                event_id=event_id,
                group=group,
                day_index=day,
                code=code,
                label=str(label).strip(),
                is_active=True,
                created_by=created_by,
                created_at=created_at,
            )
            session.add(row)
        results.append(row)
    session.flush()
    return results

def update_prompt(
    session: Session,
    prompt_id: int,
    *,
    label: Optional[str] = None,
    is_active: Optional[bool] = None,
    day_index: Optional[int] = None,
    group: Optional[str] = None,
    modified_by: Optional[str] = None,
    modified_at: Optional[str] = None,
) -> EventPrompt | None:
    """
    Update a prompt's label, active status, day_index, and/or group.
    """
    row = session.get(EventPrompt, prompt_id)
    if not row:
        return None
    if label is not None:
        row.label = label.strip()
    if is_active is not None:
        row.is_active = bool(is_active)
    if day_index is not None:
        row.day_index = day_index
    if group is not None:
        row.group = group
    row.modified_by = modified_by
    row.modified_at = modified_at
    session.flush()
    return row

def delete_prompt_safe(session: Session, prompt_id: int) -> bool:
    """
    Safe delete: only delete if never used; otherwise return False.
    """
    used = session.query(UserActionPrompt.id).filter(UserActionPrompt.event_prompt_id == prompt_id).first()
    if used:
        return False
    row = session.get(EventPrompt, prompt_id)
    if not row:
        return False
    session.delete(row)
    session.flush()
    return True

# ---------- USER ACTION <-> PROMPTS ----------

def replace_user_action_prompts(
    session: Session,
    *,
    user_action_id: int,
    event_prompt_ids: Iterable[int],
) -> list[UserActionPrompt]:
    """
    Replace all selections for this action with the given prompt IDs.
    """
    session.query(UserActionPrompt).filter(UserActionPrompt.user_action_id == user_action_id).delete()
    out: list[UserActionPrompt] = []
    seen: set[int] = set()
    for pid in event_prompt_ids:
        if pid in seen:
            continue
        seen.add(pid)
        row = UserActionPrompt(user_action_id=user_action_id, event_prompt_id=pid)
        session.add(row)
        out.append(row)
    session.flush()
    return out

def get_prompts_for_action_event_picker(
    session: Session,
    action_event_id: int,
) -> list[EventPrompt]:
    """
    Respect ActionEvent.prompts_group:
      - NULL => all groups
      - "sfw"/"nsfw"/other => only that group
    """
    ae = session.get(ActionEvent, action_event_id)
    if not ae:
        return []

    # Find the event_id for this AE
    event_id = ae.event_id
    group = getattr(ae, "prompts_group", None)

    return get_prompts_for_event(session, event_id=event_id, group=group, active_only=True)

# ---------- REPORTING HELPERS ----------

def count_prompt_popularity_for_event(session: Session, event_id: int) -> list[tuple[EventPrompt, int]]:
    """
    Returns (EventPrompt, usage_count) ordered by popularity desc.
    """
    q = (
        session.query(EventPrompt, func.count(UserActionPrompt.id).label("uses"))
        .outerjoin(UserActionPrompt, UserActionPrompt.event_prompt_id == EventPrompt.id)
        .filter(EventPrompt.event_id == event_id, EventPrompt.is_active.is_(True))
        .group_by(EventPrompt.id)
        .order_by(func.count(UserActionPrompt.id).desc(), func.lower(EventPrompt.label))
    )
    return q.all()

def count_user_prompt_stats_for_event(
    session: Session,
    event_id: int,
    user_id: int,
) -> tuple[int, int]:
    """
    Returns (total_prompts_tagged, unique_prompts_done) for the user's actions in this event.
    """
    
    total_q = (
        session.query(func.count(UserActionPrompt.id))
        .join(UserAction, UserAction.id == UserActionPrompt.user_action_id)
        .join(EventPrompt, EventPrompt.id == UserActionPrompt.event_prompt_id)
        .filter(UserAction.user_id == user_id, EventPrompt.event_id == event_id)
    )
    unique_q = (
        session.query(func.count(func.distinct(UserActionPrompt.event_prompt_id)))
        .join(UserAction, UserAction.id == UserActionPrompt.user_action_id)
        .join(EventPrompt, EventPrompt.id == UserActionPrompt.event_prompt_id)
        .filter(UserAction.user_id == user_id, EventPrompt.event_id == event_id)
    )
    total = total_q.scalar() or 0
    unique_ = unique_q.scalar() or 0
    return total, unique_