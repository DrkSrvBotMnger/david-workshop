from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional
from bot.utils.time_parse_paginate import now_iso
from db.schema import User, Action, UserAction, ActionEvent
import discord
from bot.domain.dto import UserDTO
from bot.domain.mapping import user_to_dto

def get_or_create_user_dto(session, member: discord.Member) -> UserDTO:

    discord_id=str(member.id)
    user = get_user_by_discord_id(session, discord_id)
    if user:
    
        user_data={
            "username": member.name,
            "display_name": member.global_name,
            "nickname": member.nick
        }
        for key, value in user_data.items():
            setattr(user, key, value)
    
        user.modified_at=now_iso()
        session.flush()
        return user_to_dto(user)
    
    user_data={
        "username": member.name,
        "display_name": member.global_name,
        "nickname": member.nick
    }
    user = User(**user_data, user_discord_id=discord_id, created_at=now_iso())    
    session.add(user)
    session.flush()
    return user_to_dto(user)



# --- GET ---
def get_user_by_discord_id(
    session: Session, 
    user_discord_id: str
) -> Optional[User]:
    """Retrieve a user by its discord id."""
    
    return session.query(User).filter_by(user_discord_id=user_discord_id).first()


# --- CREATE ---
def get_or_create_user(session, member: discord.Member) -> User:

    discord_id=str(member.id)
    user = get_user_by_discord_id(session, discord_id)
    if user:

        user_data={
            "username": member.name,
            "display_name": member.global_name,
            "nickname": member.nick
        }
        for key, value in user_data.items():
            setattr(user, key, value)

        user.modified_at=now_iso()
        session.flush()
        return user

    user_data={
        "username": member.name,
        "display_name": member.global_name,
        "nickname": member.nick
    }
    user = User(**user_data, user_discord_id=discord_id, created_at=now_iso())    
    session.add(user)
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