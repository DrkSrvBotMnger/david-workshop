from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional
from bot.config import EXCLUDED_LOG_FIELDS
from bot.crud import general_crud
from bot.utils import now_iso
from db.schema import Event, EventLog, EventStatus


# --- GET ---
def get_event_by_key(
    session: Session, 
    event_key: str
) -> Optional[Event]:
    """Retrieve an event by its internal event_key."""
 
    return session.query(Event).filter_by(event_key=event_key).first()


def get_event_by_id(
    session: Session, 
    event_id: int
) -> Optional[Event]:
    """Retrieve an event by its internal event_key."""

    return session.query(Event).filter_by(id=event_id).first()


# --- CREATE ---
def create_event(
    session: Session,
    event_create_data: dict
) -> Event:
    """Create a new event and log the action."""
    
    iso_now=now_iso()
    
    event_create_data.setdefault("event_status", EventStatus.draft)
    event_create_data.setdefault("created_at", iso_now)

    event = Event(**event_create_data)  
    session.add(event)
    session.flush()  # Needed to get reward.id for log
    
    # Log event creation
    general_crud.log_change(
        session=session,
        log_model=EventLog,
        fk_field="event_id",
        fk_value=event.id,
        log_action="create",
        performed_by=event.created_by,
        performed_at=iso_now,
        log_description=f"Event created: {event.event_name} ({event.event_key})"
    )

    return event


# --- UPDATE ---
def update_event(
    session: Session,
    event_key: str,
    event_update_data: dict, 
    reason: Optional[str] = None
) -> Optional[Event]:
    """
    Update an event with the given updates dict and log the action.
    Returns updated Event or None if not found.
    """
    
    event = get_event_by_key(
        session=session, 
        event_key=event_key
    )
    if not event:
        return None

    iso_now = now_iso()
    event_update_data["modified_at"] =  iso_now    
    for key, value in event_update_data.items():
        setattr(event, key, value)

    updated_fields = [k for k in event_update_data.keys() if k not in EXCLUDED_LOG_FIELDS]
        
    log_description = f"Event {event.event_name} ({event.event_key}) updated."
    if reason:
        log_description += f" Reason: {reason}"
    log_description += f" Updated fields: {', '.join(updated_fields)}" 

    general_crud.log_change(
        session=session,
        log_model=EventLog,
        fk_field="event_id",
        fk_value=event.id,
        log_action="edit",
        performed_by=event.modified_by,
        performed_at=iso_now,
        log_description=log_description
    )

    return event


# --- DELETE ---
def delete_event(
    session: Session,
    event_key: str, 
    performed_by: str,
    reason: str
) -> bool:
    """Delete an event and log the action."""

    event = get_event_by_key(
        session=session, 
        event_key=event_key
    )
    
    if not event:
        return False
        
    iso_now=now_iso()
    
    # Log event deletion
    general_crud.log_change(
        session=session, 
        log_model=EventLog,
        fk_field="event_id",
        fk_value=event.id,
        log_action="delete", 
        performed_by=performed_by,
        performed_at=iso_now,
        log_description= f"Deleted event: {event.event_name} ({event.event_key}) deleted. Reason: {reason}"
    )

    session.delete(event)
    
    return True

    
# --- LIST ---
def get_all_events(
    session: Session, 
    tag: Optional[str] = None, 
    event_status: Optional[str] = None,
    mod_by_discord_id: Optional[str] = None
) -> list[Event]:
    """
    Retrieve events with optional filters.
    - tag: partial match on one of the tags
    - event_status: match on the status
    - mod_id: Discord id of moderator
    """
    
    query = session.query(Event)

    if tag:
        query = query.filter(Event.tags.ilike(f"%{tag}%"))
    if event_status is not None:
        query = query.filter(Event.event_status == EventStatus(event_status))
    if mod_by_discord_id:
        query = query.filter(or_(Event.created_by == mod_by_discord_id, Event.modified_by == mod_by_discord_id))

    return query.order_by(
        Event.modified_at.desc().nullslast(),
        Event.created_at.desc()
    ).all()


# --- LIST LOGS ---
def get_event_logs(
    session: Session, 
    log_action: Optional[str] = None,
    performed_by: Optional[str] = None
) -> list[EventLog]:
    """
    Retrieve event logs with optional filters.
    - action: 'create', 'edit', 'delete'
    - performed_by: Discord ID of moderator
    """
    
    query = (
        session.query(EventLog)
        .join(Event, Event.id == EventLog.event_id, isouter=True)
    )

    if log_action:
        query = query.filter(EventLog.log_action == log_action.lower())
    if performed_by:
        query = query.filter(EventLog.performed_by == performed_by)

    return query.order_by(EventLog.performed_at.desc()).all()


# --- VALIDATE ---
def is_event_active(
    session: Session, 
    event_id: int
) -> bool:
    """Returns True if the event is active."""
    
    event = session.query(Event).filter_by(id=event_id).first()
    
    return bool(event and event.event_status == EventStatus.active)


# --- SET STATUS ---
def set_event_status(
    session: Session, 
    event_key: str, 
    status_update_data: dict
) -> Optional[Event]:
    """
    Set the status of an event and log the action.
    status_update_data should include:
        - event_status: EventStatus
        - modified_by: str
    """
    
    event = get_event_by_key(session=session, event_key=event_key)
    if not event:
        return None
        
    new_status = status_update_data.get("event_status")
    iso_now = now_iso()

    # Apply updates
    status_update_data["modified_at"] = iso_now
    for key, value in status_update_data.items():
        setattr(event, key, value)

    log_description = f"Event status changed to {new_status.value}."

    general_crud.log_change(
        session=session,
        log_model=EventLog,
        fk_field="event_id",
        fk_value=event.id,
        log_action="edit",
        performed_by=event.modified_by,
        performed_at=iso_now,
        log_description=log_description
    )

    return event