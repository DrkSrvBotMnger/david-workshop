from sqlalchemy import or_
from sqlalchemy.orm import Session
from bot.crud import general_crud
from bot.utils import now_iso
from db.schema import ActionEvent, Action, ActionEventLog, Event


# --- GET ---
def get_action_event_by_key(
    session, 
    action_event_key
):
    return session.query(ActionEvent).filter_by(action_event_key=action_event_key).first()

def get_action_events_for_event(
    session, 
    event_id
):
    return session.query(ActionEvent).filter_by(event_id=event_id).all()


# --- CREATE ---
def create_action_event(
    session, 
    action_id, 
    event_id, 
    created_by, 
    points_granted=0, 
    reward_event_id=None,
    self_reportable=True, 
    input_help_text=None
):
    ae = ActionEvent( 
        action_id=action_id,
        event_id=event_id,
        points_granted=points_granted,
        reward_event_id=reward_event_id,
        self_reportable=self_reportable,
        input_help_text=input_help_text,
        created_by=created_by,
        created_at=now_iso()
    )
    session.add(ae)
    session.flush()  # To get ID

    general_crud.log_change(
        session=session,
        log_model=ActionEventLog,
        fk_field="id",
        fk_value=ae.id,
        action="create",
        performed_by=created_by,
        description=f"Linked action {action_id} to event {event_id}."
    )
    
    return ae
    

# --- UPDATE ---
def update_action_event(
    session, 
    action_event_id, 
    **kwargs
):
    ae = get_action_event(session, action_event_id)
    if not ae:
        return None
    for key, value in kwargs.items():
        if hasattr(ae, key):
            setattr(ae, key, value)
    return ae


# --- DELETE ---
def delete_action_event(
    session, 
    action_event_id
):
    ae = get_action_event(session, action_event_id)
    if not ae:
        return False
    session.delete(ae)
    return True