from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional
from bot.crud import general_crud
from bot.utils.time_parse_paginate import now_iso
from db.schema import User, UserAction


# --- GET ---
def get_user_by_discord_id(
    session: Session, 
    user_discord_id: str
) -> Optional[User]:
    """Retrieve a user by its discord id."""
    
    return session.query(User).filter_by(user_discord_id=user_discord_id).first()


# --- CREATE ---
def get_or_create_user(session, discord_id: str, user_data: dict) -> User:
    user = session.query(User).filter_by(user_discord_id=discord_id).first()
    print(f"✅ User fetched: {user}")
    if user:

        for key, value in user_data.items():
            setattr(user, key, value)

        user.modified_at=now_iso()
        print(f"✅ User updated: {user}")
        session.flush()
        return user

    user = User(**user_data, user_discord_id=discord_id, created_at=now_iso())    
    session.add(user)
    print(f"✅ User created: {user}")
    session.flush()
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