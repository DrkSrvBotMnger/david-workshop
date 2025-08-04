from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional
from bot.crud import general_crud
from bot.utils import now_iso
from db.schema import RewardEvent, Reward, Event


# --- GET ---
def get_reward_event_by_key(
    session: Session, 
    reward_event_key: str
) -> Optional[Reward]:
    return session.query(RewardEvent).filter_by(reward_event_key=reward_event_key).first()

#def get_rewards_for_event(
#    session: Session, 
#    event_id
#) -> list[RewardEvent]:
#    return session.query(RewardEvent).filter_by(event_id=event_id).all()


# --- UPDATE ---
def update_reward_event(
    session, 
    reward_event_id, 
    **kwargs
):
    re = get_reward_event(session, reward_event_id)
    if not re:
        return None
    for key, value in kwargs.items():
        if hasattr(re, key):
            setattr(re, key, value)
    return re


# --- DELETE ---
def delete_reward_event(
    session, 
    reward_event_id
):
    re = get_reward_event(session, reward_event_id)
    if not re:
        return False
    session.delete(re)
    return True



# ---------------------------
# REWARD EVENTS
# ---------------------------

# --- CREATE ---
def create_reward_event(
    session, 
    event_id, 
    reward_id, 
    availability="inshop", 
    price=0
):
    re = RewardEvent(
        event_id=event_id,
        reward_id=reward_id,
        availability=availability,
        price=price
    )
    session.add(re)
    return re
    
def create_reward_event(
    session: Session, 
    reward_id,
    event_id,
    availability="inshop",
    price=0,
    created_by=None,
    reason=None
):
    re = RewardEvent(
        reward_id=reward_id,
        event_id=event_id,
        availability=availability,
        price=price
    )
    session.add(re)
    session.flush()

    log_change(
        session=session,
        table_name="reward_event_logs",
        target_id=re.id,
        action="create",
        performed_by=created_by,
        description=reason or f"Linked reward {reward_id} to event {event_id}."
    )
    return re.id


def update_reward_event(
    session,
    reward_event_id,
    availability=None,
    price=None,
    modified_by=None,
    reason=None
):
    re = session.get(RewardEvent, reward_event_id)
    if not re:
        return None

    if availability is not None:
        re.availability = availability
    if price is not None:
        re.price = price

    log_change(
        session=session,
        table_name="reward_event_logs",
        target_id=reward_event_id,
        action="edit",
        performed_by=modified_by,
        description=reason or f"Edited RewardEvent {reward_event_id}."
    )
    return re.id


def delete_reward_event(session, reward_event_id, deleted_by=None, reason=None):
    re = session.get(RewardEvent, reward_event_id)
    if not re:
        return None
    session.delete(re)

    log_change(
        session=session,
        table_name="reward_event_logs",
        target_id=reward_event_id,
        action="delete",
        performed_by=deleted_by,
        description=reason or f"Unlinked RewardEvent {reward_event_id}."
    )
    return reward_event_id