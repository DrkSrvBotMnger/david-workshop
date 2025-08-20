# bot/crud/action_events_crud.py
from __future__ import annotations

from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
from typing import Optional, List, Iterable, Sequence, Tuple
from bot.crud import general_crud
from db.schema import Action, ActionEvent, Event, RewardEvent, UserAction, Reward, ActionEventLog

# --- READ: candidates for user self-report in one event ---
def list_self_reportable_action_events_for_event(
    session: Session,
    event_id: int,
) -> list[tuple[ActionEvent, Action, RewardEvent | None, Event]]:
    """
    Returns tuples (ae, action, revent, event) for a single event where:
      - Action.is_active is True and Action.deactivated_at is NULL
      - ActionEvent.is_self_reportable is True
    NOTE: user-based checks (repeatability), and event-status gating are handled in the service layer.
    """
    q = (
        session.query(ActionEvent, Action, RewardEvent, Event)
        .join(Action, ActionEvent.action_id == Action.id)
        .join(Event, ActionEvent.event_id == Event.id)
        .outerjoin(RewardEvent, RewardEvent.id == ActionEvent.reward_event_id)
        .filter(ActionEvent.event_id == event_id)
        .filter(and_(Action.is_active.is_(True), Action.deactivated_at.is_(None)))
        .filter(ActionEvent.is_self_reportable.is_(True))
    )

    out: list[tuple[ActionEvent, Action, RewardEvent | None, Event]] = []
    for row in q.all():
        ae, action, revent, ev = row  # unpack Row -> real tuple
        out.append((ae, action, revent, ev))
    return out

# --- READ: active action-event in one event ---
def list_action_events_for_event(
    session: Session,
    event_id: int,
) -> list[tuple[ActionEvent, Action, RewardEvent | None, Event]]:
    """
    Returns tuples (ae, action, revent, event) for a single event where:
      - Action.is_active is True and Action.deactivated_at is NULL
    """
    q = (
        session.query(ActionEvent, Action, RewardEvent, Event)
        .join(Action, ActionEvent.action_id == Action.id)
        .join(Event, ActionEvent.event_id == Event.id)
        .outerjoin(RewardEvent, RewardEvent.id == ActionEvent.reward_event_id)
        .filter(ActionEvent.event_id == event_id)
        .filter(and_(Action.is_active.is_(True), Action.deactivated_at.is_(None)))
    )

    out: list[tuple[ActionEvent, Action, RewardEvent | None, Event]] = []
    for row in q.all():
        ae, action, revent, ev = row  # unpack Row -> real tuple
        out.append((ae, action, revent, ev))
    return out

# --- READ: fetch 1 AE bundle by id (used on submit) ---
def get_action_event_bundle(
    session: Session,
    action_event_id: int,
) -> tuple[ActionEvent, Action, RewardEvent | None, Event] | None:
    """
    Returns (ae, action, revent, event) or None.
    """
    row = (
        session.query(ActionEvent, Action, RewardEvent, Event)
        .join(Action, ActionEvent.action_id == Action.id)
        .join(Event, ActionEvent.event_id == Event.id)
        .outerjoin(RewardEvent, RewardEvent.id == ActionEvent.reward_event_id)
        .filter(ActionEvent.id == action_event_id)
        .first()
    )
    if row is None:
        return None
    ae, action, revent, ev = row  # unpack Row -> real tuple
    return ae, action, revent, ev

# --- READ: repeatability check (non-repeatable already done?) ---
def user_already_completed_non_repeatable(
    session: Session,
    user_id: int,
    action_event_id: int,
) -> bool:
    exists = (
        session.query(UserAction.id)
        .filter(UserAction.user_id == user_id, UserAction.action_event_id == action_event_id)
        .first()
    )
    return exists is not None

# ---Quick existence map for event pickers ---
def list_event_ids_with_any_self_reportable_action(
    session: Session,
    event_ids: list[int],
) -> dict[int, bool]:
    if not event_ids:
        return {}
    rows = (
        session.query(ActionEvent.event_id)
        .join(Action, ActionEvent.action_id == Action.id)
        .filter(ActionEvent.event_id.in_(event_ids))
        .filter(and_(Action.is_active.is_(True), Action.deactivated_at.is_(None)))
        .filter(ActionEvent.is_self_reportable.is_(True))
        .distinct()
        .all()
    )
    present = {ev_id for (ev_id,) in rows}
    return {eid: (eid in present) for eid in event_ids}







# --- old crud to be replaced

def get_action_event(session: Session, action_event_id: int) -> Optional[ActionEvent]:
    return session.query(ActionEvent).get(action_event_id)        # type: ignore

def get_reward_event(session: Session, reward_event_id: int) -> Optional[RewardEvent]:
    return session.query(RewardEvent).get(reward_event_id)

def get_reward(session: Session, reward_id: int) -> Optional[Reward]:
    return session.query(Reward).get(reward_id)



# --- Old CRUD functions to be reworked ---
# --- GET ---
def get_action_event_by_key(
    session, 
    action_event_key
) -> Optional[ActionEvent]:
    """Retrieve an action event by its key."""
    
    return session.query(ActionEvent).filter_by(action_event_key=action_event_key).first()


def get_action_events_for_event(
    session: Session,
    event_id: int
) -> List[ActionEvent]:
    """Return all action-events linked to a specific event."""
    return (
        session.query(ActionEvent)
        .filter_by(event_id=event_id)
        .all()
    )


# --- CREATE ---
def create_action_event(
    session: Session, 
    ae_create_data: dict,
    force: bool = False
) -> ActionEvent:
    """Create a new action event and log the action."""

    ae = ActionEvent(**ae_create_data)
    session.add(ae)
    session.flush()  # Needed to get reward.id for log

    general_crud.log_change(
        session=session,
        log_model=ActionEventLog,
        fk_field="action_event_id",
        fk_value=ae.id,
        log_action="create",
        performed_by=ae.created_by,
        performed_at=ae.created_at,
        log_description=f"Linked action {ae.action_id} to event {ae.event_id}. Shortcode: '{ae.action_event_key}'.",
        forced=force
    )
    
    return ae
    

# --- UPDATE ---
def update_action_event(
    session: Session,
    action_event_key: str,
    ae_update_data: dict, 
    force: bool = False
) -> Optional[ActionEvent]:
    """
    Update an action event with the given updates dict and log the action.
    Returns updated ActionEvent or None if not found.
    """
    
    ae = get_action_event_by_key(
        session=session, 
        action_event_key=action_event_key
    )
    if not ae:
        return None
          
    for key, value in ae_update_data.items():
        setattr(ae, key, value)

    general_crud.log_change(
        session=session,
        log_model=ActionEventLog,
        fk_field="action_event_id",
        fk_value=ae.id,
        log_action="edit",
        performed_by=ae.modified_by,
        performed_at=ae.modified_at,
        log_description= f"Action-Event link '{action_event_key}' updated.",
        forced=force
    )

    return ae

# --- DELETE ---
def delete_action_event(
    session: Session,
    action_event_key: str, 
    performed_by: str,
    performed_at: str,
    force: bool = False
) -> bool:
    """Delete an event and log the action."""

    ae = get_action_event_by_key(
        session=session, 
        action_event_key=action_event_key
    )
    
    if not ae:
        return False

    # Log event deletion
    general_crud.log_change(
        session=session, 
        log_model=ActionEventLog,
        fk_field="action_event_id",
        fk_value=ae.id,
        log_action="delete", 
        performed_by=performed_by,
        performed_at=performed_at,
        log_description= f"Unlinked Action-Event '{action_event_key}'.",
        forced=force
    )

    session.delete(ae)

    return True