from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional, List
from bot.crud import general_crud
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