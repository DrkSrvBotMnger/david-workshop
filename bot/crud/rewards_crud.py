from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional
from bot.crud import general_crud
from bot.utils.time_parse_paginate import now_iso
from db.schema import Reward, RewardLog, RewardEvent, Event, EventStatus

def get_reward_by_reward_event_id(session: Session, reward_event_id: int) -> Reward | None:
    revent = session.query(RewardEvent).get(reward_event_id)
    if not revent:
        return None
    return session.query(Reward).get(revent.reward_id)

def increment_reward_number_granted(session: Session, reward_id: int, delta: int = 1) -> None:
    if not delta:
        return
    reward = session.query(Reward).get(reward_id)
    if not reward:
        return
    reward.number_granted = (reward.number_granted or 0) + delta
    session.flush()



# ------------------------------ Old CRUD functions to be reworked ------------------------------
# --- GET ---
def get_reward_by_key(
    session: Session, 
    reward_key: str
) ->  Optional[Reward]:
    """Retrieve a reward by its internal reward_key."""
    
    return session.query(Reward).filter_by(reward_key=reward_key).first()


# --- CREATE ---
def create_reward(
    session: Session, 
    reward_create_data: dict
) -> Reward:
    """
    Create a new reward and log the action.
    """
    
    iso_now=now_iso()
    reward = Reward(**reward_create_data, created_at=iso_now)    
    session.add(reward)
    session.flush()  # Needed to get reward.id for log

    general_crud.log_change(
        session=session,
        log_model=RewardLog,
        fk_field="reward_id",
        fk_value=reward.id,
        log_action="create",
        performed_by=reward.created_by,
        performed_at=iso_now,
        log_description=f"Reward created: {reward.reward_name} ({reward.reward_key})"
    )
    
    return reward
    

# --- UPDATE ---
def update_reward(
    session: Session, 
    reward_key: str, 
    reward_update_data: dict, 
    reason: Optional[str] = None,
    forced: bool = False
) -> Optional[Reward]:
    """
    Update a reward with the given updates dict and log the action.
    Returns updated Reward or None if not found.
    """

    reward = get_reward_by_key(
        session=session, 
        reward_key=reward_key
    )
    if not reward:
        return None

    iso_now=now_iso()
    for key, value in reward_update_data.items():
        setattr(reward, key, value)

    reward.modified_at = iso_now
    
    log_description = f"Reward {reward.reward_name} ({reward.reward_key}) updated."
    if reason:
        log_description += f" Reason: {reason}"
    log_description += f" Updated fields: {', '.join(reward_update_data.keys())}" 
    
    general_crud.log_change(
        session=session,
        log_model=RewardLog,
        fk_field="reward_id",
        fk_value=reward.id,
        log_action="edit",
        performed_by=reward.modified_by,
        performed_at=iso_now,
        log_description=log_description,
        forced=forced
    )

    return reward


# --- DELETE ---
def delete_reward(
    session: Session, 
    reward_key: str, 
    performed_by: str,
    reason: str,
    forced: bool = False
) -> bool:
    """Delete a reward and log the action."""
    
    reward = get_reward_by_key(
        session=session, 
        reward_key=reward_key
    )
    if not reward:
        return False
    
    iso_now=now_iso()
    
    general_crud.log_change(
        session=session,
        log_model=RewardLog,
        fk_field="reward_id",
        fk_value=reward.id,
        log_action="delete",
        performed_by=performed_by,
        performed_at=iso_now,
        log_description=f"Deleted reward: {reward.reward_name} ({reward.reward_key}). Reason: {reason}",
        forced=forced
    )

    session.delete(reward)
    
    return True


# --- LIST ---
def get_all_rewards(
    session: Session, 
    reward_type: Optional[str] = None,
    reward_name: Optional[str] = None,
    mod_by_discord_id: Optional[str] = None
) -> list[Reward]:
    """
    Retrieve rewards with optional filters:
    - reward_type: 'title', 'badge', 'preset', 'dynamic'
    - reward_name: partial match on reward name
    - mod_discord_id: Discord id of moderator
    """
    
    query = session.query(Reward)

    if reward_type:
        query = query.filter(Reward.reward_type.ilike(reward_type))
    if reward_name:
        query = query.filter(Reward.reward_name.ilike(f"%{reward_name}%"))
    if mod_by_discord_id:
        query = query.filter(
            or_(Reward.created_by == mod_by_discord_id, Reward.modified_by == mod_by_discord_id)
        )

    return query.order_by(
        Reward.modified_at.desc().nullslast(),
        Reward.created_at.desc()
    ).all()


# --- LIST LOGS ---
def get_reward_logs(
    session: Session, 
    log_action: Optional[str] = None,
    performed_by: Optional[str] = None
) -> list[RewardLog]:
    """
    Retrieve reward logs with optional filters:
    - log_action: 'create', 'edit', 'delete'
    - performed_by: Discord id of moderator
    """
    
    query = (
        session.query(RewardLog)
        .join(Reward, Reward.id == RewardLog.reward_id, isouter=True)
    )

    if log_action:
        query = query.filter(RewardLog.log_action == log_action.lower())
    if performed_by:
        query = query.filter(RewardLog.performed_by == performed_by)

    return query.order_by(RewardLog.performed_at.desc()).all()


# --- PUBLISH ---
def publish_preset(
    session: Session,
    reward_key: str,
    use_channel_discord_id: str,
    use_message_discord_id: str,
    use_header_message_discord_id: str, 
    set_by_discord_id: str,
    forced: bool = False
) -> Optional[Reward]:
    """
    Update a reward's approved preset details.
    Also logs the publish action.
    """
    
    reward = get_reward_by_key(
        session=session, 
        reward_key=reward_key
    )
    if not reward:
        return None
        
    iso_now=now_iso()
    reward.use_channel_discord_id = str(use_channel_discord_id)
    reward.use_message_discord_id = str(use_message_discord_id)
    reward.use_header_message_discord_id = str(use_header_message_discord_id)  # header
    reward.preset_by = str(set_by_discord_id)
    reward.preset_at = iso_now
    reward.modified_by = set_by_discord_id
    reward.modified_at = iso_now

    general_crud.log_change(
        session=session,
        log_model=RewardLog,
        fk_field="reward_id",
        fk_value=reward.id,
        log_action="edit",
        performed_by=set_by_discord_id,
        performed_at=iso_now,
        log_description=f"Published/updated preset for reward `{reward.reward_key}`.",
        forced=forced
    )

    return reward
    

# --- VALIDATE ---
def reward_is_linked_to_active_event(
    session: Session,
    reward_key: str
) -> bool:
    """Returns True if a reward is linked to at least one active event."""

    return (
        session.query(RewardEvent)
        .join(Event, Event.id == RewardEvent.event_id)
        .join(Reward, Reward.id == RewardEvent.reward_id)
        .filter(
            Reward.reward_key == reward_key,
            Event.event_status == EventStatus.active
        )
        .count()
        > 0
    )