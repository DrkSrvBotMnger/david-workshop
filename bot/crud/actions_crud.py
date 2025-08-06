from sqlalchemy.orm import Session
from typing import Optional
from bot.utils import now_iso
from db.schema import Action, ActionEvent
from bot.crud import general_crud


# --- GET ---
def get_action_by_key(
    session: Session,
    action_key: str
) -> Optional[Action]:
    """Retrieve an action by its internal action_key."""
    
    return session.query(Action).filter_by(action_key=action_key).first()


# --- CREATE ---
def create_action(
    session: Session,
    action_create_data: dict
) -> Action:
    """Create a new action."""

    iso_now=now_iso()
    action = Action(**action_create_data, created_at=iso_now)    
    session.add(action)
    
    return action


# --- UPDATE ---
def deactivate_action(
    session: Session,
    action_key: str,
    action_update_data: dict
) -> Optional[Action]:

    action = get_action_by_key(
        session=session,
        action_key=action_key
    )

    if not action:
        return None

    iso_now = now_iso()
    action_update_data["deactivated_at"] =  iso_now    
    for key, value in action_update_data.items():
        setattr(action, key, value)

    return action


# --- DELETE ---
def delete_action(
    session: Session,
    action_key: str
) -> bool:

    action = get_action_by_key(
        session=session,
        action_key=action_key
    )

    if not action:
        return False

    session.delete(action)

    return True


# --- LIST ---
def get_all_actions(
    session: Session,
    is_active: Optional[bool] = None,
    key_search: Optional[str] = None,
    order_by: str = "created_at" or "key"
) -> list[Action]:
    """
    Retrieve actions with optional filters:
    - active: True/False to filter by status
    - key_search: partial match on action_key
    - order_by: 'created_at' or 'key'
    """
    
    query = session.query(Action)

    if is_active is not None:
        query = query.filter(Action.is_active == is_active)

    if key_search:
        query = query.filter(Action.action_key.ilike(f"%{key_search}%"))

    if order_by == "key":
        query = query.order_by(Action.action_key.asc())
    elif order_by == "created_at":
        query = query.order_by(Action.created_at.desc())

    return query.all()


# --- VALIDATE ---
def action_is_linked_to_active_event(
    session: Session,
    action_key: str
) -> bool:
    """Returns True if a reward is linked to any active event."""

    return general_crud.is_linked_to_active_event(
        session=session,
        link_model=ActionEvent,
        link_field_name="action_id",
        key_lookup_func=get_action_by_key,
        public_key=action_key
    )