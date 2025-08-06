from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional, List
from bot.config import EXCLUDED_LOG_FIELDS
from bot.crud import general_crud
from bot.utils import now_iso
from db.schema import ActionEvent, ActionEventLog


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
    ae_create_data: dict
) -> ActionEvent:
    """Create a new action event and log the action."""

    iso_now=now_iso()

    ae_create_data.setdefault("created_at", iso_now)

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
        performed_at=iso_now,
        log_description=f"Linked action {ae.action_id} to event {ae.event_id}. Shortcode: '{ae.action_event_key}'."
    )
    
    return ae
    

# --- UPDATE ---
def update_action_event(
    session: Session,
    action_event_key: str,
    ae_update_data: dict, 
    reason: Optional[str] = None
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
        
    iso_now = now_iso()
    ae_update_data["modified_at"] =  iso_now    
    for key, value in ae_update_data.items():
        setattr(ae, key, value)

    updated_fields = [k for k in ae_update_data.keys() if k not in EXCLUDED_LOG_FIELDS]

    log_description = f"Action-Event link '{action_event_key}' updated."
    if reason:
        log_description += f" Reason: {reason}"
    log_description += f" Updated fields: {', '.join(updated_fields)}" 

    general_crud.log_change(
        session=session,
        log_model=ActionEventLog,
        fk_field="action_event_id",
        fk_value=ae.id,
        log_action="edit",
        performed_by=ae.modified_by,
        performed_at=iso_now,
        log_description=log_description
    )

    return ae

# --- DELETE ---
def delete_action_event(
    session: Session,
    action_event_key: str, 
    performed_by: str,
    reason: str
) -> bool:
    """Delete an event and log the action."""

    ae = get_action_event_by_key(
        session=session, 
        action_event_key=action_event_key
    )
    
    if not ae:
        return False

    iso_now=now_iso()

    # Log event deletion
    general_crud.log_change(
        session=session, 
        log_model=ActionEventLog,
        fk_field="action_event_id",
        fk_value=ae.id,
        log_action="delete", 
        performed_by=performed_by,
        performed_at=iso_now,
        log_description= f"Unlinked Action-Event '{action_event_key}'. Reason: {reason}."
    )

    session.delete(ae)

    return True