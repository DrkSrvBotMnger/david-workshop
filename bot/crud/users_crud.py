from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional
from bot.crud import general_crud
from bot.utils import now_iso
from db.schema import User, UserAction


# --- GET ---
def get_user_by_discord_id(
    session: Session, 
    user_discord_id: str
) -> Optional[User]:
    """Retrieve a user by its discord id."""
    
    return session.query(User).filter_by(user_discord_id=user_discord_id).first()


# --- CREATE OR GET ---
def get_or_create_user(
    session: Session, 
    user_discord_id: str,
    user_create_data: Optional[dict] = None,
) -> User:
    """
    Retrieve or create a new user and log the action.
    """
    
    user = get_user_by_discord_id(
        session=session,
        user_discord_id=user_discord_id
    )

    if not user:

        iso_now=now_iso()
        
        user = User(
            user_discord_id=user_discord_id,
            created_at=iso_now,
            **(user_create_data or {})
        )
        session.add(user)
        
    return user


# --- UPDATE ---
def update_user(
    session: Session, 
    user_discord_id: str,
    user_update_data: dict,
) -> Optional[User]:
    """Update a user's names."""
    
    user = get_user_by_discord_id(
        session=session,
        user_discord_id=user_discord_id
    )
    
    if not user:
        return None
        
    iso_now=now_iso()
    
    for key, value in user_update_data.items():
        if hasattr(user, key):
            setattr(user, key, value)

    user.modified_at = iso_now
    
    return user


# --- VALIDATE ---
def action_is_used(
    session: Session, 
    action_id: int
) -> bool:
    """Return True if any UserAction references this action_key."""
    
    return session.query(UserAction).filter(UserAction.action_id == action_id).first() is not None