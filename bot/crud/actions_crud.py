from db.schema import Action
from sqlalchemy.orm import Session
from datetime import datetime

# --- CREATE ---
def create_action(session: Session, action_key: str, description: str, input_fields_json: str = None):
    action = Action(
        action_key=action_key,
        description=description,
        input_fields_json=input_fields_json,
        created_at=str(datetime.utcnow())
    )
    session.add(action)
    #session.commit()
    return action

# --- DELETE ---
def delete_action(session: Session, action_key: str):
    action = get_action_by_key(session, action_key)
    if not action:
        return False
    session.delete(action)
    #session.commit()
    return True

# --- GET ---
def get_action_by_key(session: Session, action_key: str):
    return session.query(Action).filter_by(action_key=action_key).first()

def get_action_by_id(session: Session, action_id: int):
    return session.query(Action).filter_by(id=action_id).first()

# --- LIST ---
def get_all_actions(session: Session, active: bool = None):
    query = session.query(Action)
    if active is not None:
        query = query.filter(Action.active == active)
    return query.order_by(Action.created_at.desc()).all()
