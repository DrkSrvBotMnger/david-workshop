# bot/crud/users_crud.py
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional
from bot.utils.time_parse_paginate import now_iso
from db.schema import User, Action, UserAction, ActionEvent

def get_user_by_discord_id(session: Session, user_discord_id: str) -> User | None:
    return (
        session.query(User)
        .filter(User.user_discord_id == user_discord_id)
        .first()
    )

def create_user_from_member(session: Session, member) -> User:
    user = User(
        user_discord_id=str(member.id),
        username=member.name,
        display_name=getattr(member, "display_name", None) or getattr(member, "global_name", None) or member.name,
        nickname=getattr(member, "nick", None),
        points=0,
        total_earned=0,
        total_spent=0,
        created_at=now_iso(),
        modified_at=None,
    )
    session.add(user)
    session.flush()
    return user

def update_user_identity_if_changed(session: Session, user: User, member) -> bool:
    changed = False
    new_username = member.name
    new_display  = getattr(member, "display_name", None) or getattr(member, "global_name", None) or member.name
    new_nick     = getattr(member, "nick", None)

    if user.username != new_username:
        user.username = new_username; changed = True
    if user.display_name != new_display:
        user.display_name = new_display; changed = True
    if user.nickname != new_nick:
        user.nickname = new_nick; changed = True

    if changed:
        user.modified_at = now_iso()
        session.flush()
    return changed

def get_or_create_user(session: Session, member) -> User:
    user = get_user_by_discord_id(session, str(member.id))
    if not user:
        user = create_user_from_member(session, member)
    else:
        update_user_identity_if_changed(session, user, member)
    return user



# ------------------------------

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
def ae_is_used_by_action_id(
    session: Session, 
    action_id: int
) -> bool:
    """Return True if any UserAction references this action_key."""

    return (
        session.query(UserAction)
        .join(ActionEvent, UserAction.action_event_id == ActionEvent.id)
        .join(Action, ActionEvent.action_id == Action.id)
        .filter(Action.id == action_id)
        .first()
        is not None
    )


def ae_is_used_by_ae_id(
        session: Session, 
        action_event_id: int
    ) -> bool:
        """Return True if any UserAction references this action_key."""

        return session.query(UserAction).filter(UserAction.action_event_id == action_event_id).first() is not None