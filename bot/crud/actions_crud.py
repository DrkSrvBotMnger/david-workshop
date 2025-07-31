from sqlalchemy.orm import Session
from bot.utils import now_iso
from db.schema import Action


# --- CREATE ---
def create_action(session: Session, action_key: str, description: str, input_fields_json: str = None):
    action = Action(
        action_key=action_key,
        description=description,
        input_fields_json=input_fields_json,
        created_at=now_iso()
    )
    session.add(action)
    
    return action


# --- DELETE ---
def delete_action(session: Session, action_key: str):
    action = get_action_by_key(session, action_key)
    if not action:
        return False
    session.delete(action)
    
    return True


# --- GET ---
def get_action_by_key(session: Session, action_key: str):
    return session.query(Action).filter_by(action_key=action_key).first()

def get_action_by_id(session: Session, action_id: int):
    return session.query(Action).filter_by(id=action_id).first()


# --- LIST ---
def get_all_actions(
    session: Session,
    active: bool = None,
    key_search: str = None,
    order_by: str = "created_at"  # or "key"
):
    """
    Retrieve actions with optional filters:
    - active: True/False to filter by status
    - key_search: partial match on action_key
    - order_by: 'created_at' or 'key'
    """
    query = session.query(Action)

    if active is not None:
        query = query.filter(Action.active == active)

    if key_search:
        query = query.filter(Action.action_key.ilike(f"%{key_search}%"))

    if order_by == "key":
        query = query.order_by(Action.action_key.asc())
    else:
        query = query.order_by(Action.created_at.desc())

    return query.all()

