from typing import Callable, Optional, Type
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import DeclarativeMeta
from db.schema import Event, RewardEvent, ActionEvent, Reward, Action


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
    link_model: Type[DeclarativeMeta],   # e.g., RewardEvent, ActionEvent
    link_field_name: str,                # the FK column name in link_model, e.g., "reward_id"
    key_lookup_func: Callable[[Session, str], Optional[object]],  # CRUD getter
    public_key: str                      # the user-facing unique key
) -> bool:
    """
    Checks if the object identified by public_key is linked to at least one active event.
    - session: active DB session
    - link_model: SQLAlchemy model for the linking table (RewardEvent, ActionEvent, etc.)
    - link_field_name: FK field name inside link_model that points to the object
    - key_lookup_func: CRUD function to get the object by its public key
    - public_key: the string key used to find the object (reward_key, action_key, etc.)
    Returns: bool
    """
    
    # Step 1: Find the object via its CRUD lookup
    obj = key_lookup_func(session, public_key)
    if not obj:
        return False

    # Step 2: Build the filter dynamically based on link_field_name
    link_field = getattr(link_model, link_field_name)

    # Step 3: Query the linking table for an active event
    return (
        session.query(link_model)
        .join(Event, Event.id == link_model.event_id)
        .filter(
            link_field == obj.id,
            Event.is_active.is_(True)
        )
        .count() > 0
    )
