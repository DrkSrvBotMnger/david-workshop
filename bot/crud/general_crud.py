from typing import Callable, Optional, Type
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import DeclarativeMeta
# These imports are here so callers can just reference this file without re-importing every model
from db.schema import (
    Event, EventStatus,
    Action, ActionEvent,
    Reward, RewardEvent
)


# --- LOG ---
def log_change(
    *,
    session: Session,
    log_model: Type[DeclarativeMeta],  # A SQLAlchemy model class
    fk_field: str,
    fk_value: int,
    log_action: str,
    performed_by: str,
    performed_at: str,
    log_description: Optional[str] = None,
    forced:  bool = False
) -> object:
    """Generic logging for any object with a log table."""

    if forced:
        log_description = f"⚠️ **FORCED CHANGE** — {log_description}" if log_description else "⚠️ **FORCED CHANGE**"
        
    kwargs = {
        fk_field: fk_value,
        "log_action": log_action,
        "performed_by": performed_by,
        "performed_at": performed_at,
        "log_description": log_description
    }
    log_entry = log_model(**kwargs)    
    session.add(log_entry)
    
    return log_entry


# --- ACTIVE EVENT ---
def is_linked_to_active_event(
    session: Session,
    link_model: Type[DeclarativeMeta],  # e.g., RewardEvent, ActionEvent
    link_field_name: str,  # FK column name in link_model
    key_lookup_func: Callable[[Session, str], Optional[object]],  # CRUD getter
    public_key: str,  # reward_key / action_key
) -> bool:
    """
    Checks if the object identified by public_key is linked to at least one active event.
    """

    # Step 1: Find the object via its CRUD lookup
    obj = key_lookup_func(session, public_key)
    if not obj:
        return False

    # Make sure ID exists (important for uncommitted test objects)
    session.flush()

    # Step 2: Get the linking field dynamically
    link_field = getattr(link_model, link_field_name)

    # Step 3: Query the linking table for an active event
    return (
        session.query(link_model)
        .join(Event, Event.id == link_model.event_id)
        .filter(link_field == obj.id, Event.event_status == EventStatus.active)
        .count()
        > 0
    )