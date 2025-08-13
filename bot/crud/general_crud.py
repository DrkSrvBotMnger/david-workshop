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