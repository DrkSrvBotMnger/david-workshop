# bot/crud/events_crud.py
from typing import Optional
from bot.config import EXCLUDED_LOG_FIELDS
from bot.crud import general_crud
from bot.utils.time_parse_paginate import now_iso
from db.schema import EventLog

# -----------------------------------------------------------------------------
from dataclasses import dataclass
from typing import NamedTuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from db.schema import Event, EventStatus

# ---- Generic filter spec ----------------------------------------------------

@dataclass(frozen=True)
class EventFilter:
    status_in: tuple[EventStatus, ...] | None = None
    types_in: tuple[str, ...] | None = None
    coordinator_ids: tuple[str, ...] | None = None
    has_embed: bool | None = None
    start_date_min: str | None = None
    start_date_max: str | None = None
    priority_min: int | None = None
    priority_max: int | None = None
    search_name_icontains: str | None = None
    order_by_priority_then_date: bool = True
    limit: int | None = None
    offset: int | None = None

def search_events(session: Session, f: EventFilter) -> list[Event]:
    q = session.query(Event)

    if f.status_in:
        q = q.filter(Event.event_status.in_(f.status_in))
    if f.types_in:
        q = q.filter(Event.event_type.in_(f.types_in))
    if f.coordinator_ids:
        q = q.filter(Event.coordinator_discord_id.in_(f.coordinator_ids))

    if f.has_embed is True:
        q = q.filter(
            Event.embed_channel_discord_id.isnot(None),
            Event.embed_message_discord_id.isnot(None),
        )
    elif f.has_embed is False:
        q = q.filter(
            (Event.embed_channel_discord_id.is_(None)) |
            (Event.embed_message_discord_id.is_(None))
        )

    if f.start_date_min:
        q = q.filter(Event.start_date >= f.start_date_min)
    if f.start_date_max:
        q = q.filter(Event.start_date < f.start_date_max)

    if f.priority_min is not None:
        q = q.filter(Event.priority >= f.priority_min)
    if f.priority_max is not None:
        q = q.filter(Event.priority <= f.priority_max)

    if f.search_name_icontains:
        like = f"%{f.search_name_icontains.lower()}%"
        q = q.filter(Event.event_name.ilike(like))

    if f.order_by_priority_then_date:
        q = q.order_by(Event.priority.desc(), Event.start_date.asc(), Event.event_name.asc())

    if f.offset is not None:
        q = q.offset(f.offset)
    if f.limit is not None:
        q = q.limit(f.limit)

    return q.all()

# ---- Common direct lookups / projections ------------------------------------

def get_event_by_key(session: Session, event_key: str) -> Event | None:
    return session.query(Event).filter(Event.event_key == event_key).first()

class EventMessageRefs(NamedTuple):
    event_key: str
    event_name: str
    embed_channel_discord_id: str
    embed_message_discord_id: str

def get_event_message_refs_by_key(session: Session, event_key: str) -> EventMessageRefs | None:
    row = (
        session.query(
            Event.event_key.label("event_key"),
            Event.event_name.label("event_name"),
            Event.embed_channel_discord_id.label("embed_channel_discord_id"),
            Event.embed_message_discord_id.label("embed_message_discord_id"),
        )
        .filter(Event.event_key == event_key)
        .first()
    )
    if not row or not row.embed_channel_discord_id or not row.embed_message_discord_id:
        return None
    return EventMessageRefs(row.event_key, row.event_name, row.embed_channel_discord_id, row.embed_message_discord_id)




# ------- old cruds to be repalced during refactoring -------
# --- GET ---


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