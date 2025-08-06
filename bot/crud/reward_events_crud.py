from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional, List
from bot.config import EXCLUDED_LOG_FIELDS
from bot.crud import general_crud
from bot.utils import now_iso
from db.schema import RewardEvent, Reward, Event, RewardEventLog


# --- GET ---
def get_reward_event_by_key(
    session: Session, 
    reward_event_key: str
) -> Optional[RewardEvent]:
    """Retrieve a reward event by its key."""
    
    return session.query(RewardEvent).filter_by(reward_event_key=reward_event_key).first()


def get_reward_events_for_event(
    session: Session,
    event_id: int
) -> List[RewardEvent]:
    """Return all reward-events linked to a specific event."""
    return (
        session.query(RewardEvent)
        .filter_by(event_id=event_id)
        .all()
    )


# --- CREATE ---
def create_reward_event(
    session: Session, 
    re_create_data: dict
) -> RewardEvent:
    """Create a new reward event and log the action."""

    iso_now=now_iso()
    
    re_create_data.setdefault("created_at", iso_now)

    re = RewardEvent(**re_create_data)
    session.add(re)
    session.flush()  # Needed to get reward.id for log

    # Log event creation
    general_crud.log_change(
        session=session,
        log_model=RewardEventLog,
        fk_field="reward_event_id",
        fk_value=re.id,
        log_action="create",
        performed_by=re.created_by,
        performed_at=iso_now,
        log_description=f"Linked reward {re.reward_id} to event {re.event_id}. Shortcode: '{re.reward_event_key}'.")

    return re


# --- UPDATE ---
def update_reward_event(
    session: Session,
    reward_event_key: str,
    re_update_data: dict, 
    reason: Optional[str] = None,
    forced: bool = False
) -> Optional[RewardEvent]:
    """
    Update a reward event with the given updates dict and log the action.
    Returns updated RewardEvent or None if not found.
    """

    re = get_reward_event_by_key(
        session=session, 
        reward_event_key=reward_event_key
    )
    if not re:
        return None

    iso_now = now_iso()
    re_update_data["modified_at"] =  iso_now    
    for key, value in re_update_data.items():
        setattr(re, key, value)
    
    updated_fields = [k for k in re_update_data.keys() if k not in EXCLUDED_LOG_FIELDS]        

    log_description = f"Reward-Event link '{reward_event_key}' updated."
    if reason:
        log_description += f" Reason: {reason}"
    log_description += f" Updated fields: {', '.join(updated_fields)}" 

    general_crud.log_change(
        session=session,
        log_model=RewardEventLog,
        fk_field="reward_event_id",
        fk_value=re.id,
        log_action="edit",
        performed_by=re.modified_by,
        performed_at=iso_now,
        log_description=log_description,
        forced=forced
    )

    return re


# --- DELETE ---

def delete_reward_event(
    session: Session,
    reward_event_key: str, 
    performed_by: str,
    reason: str,
    forced: bool = False
) -> bool:
    """Delete an event and log the action."""

    re = get_reward_event_by_key(
        session=session, 
        reward_event_key=reward_event_key
    )
    if not re:
        return False

    iso_now=now_iso()

    # Log event deletion
    general_crud.log_change(
        session=session, 
        log_model=RewardEventLog,
        fk_field="reward_event_id",
        fk_value=re.id,
        log_action="delete",
        performed_by=performed_by,
        performed_at=iso_now,
        log_description= f"Unlinked Reward-Event '{reward_event_key}'. Reason: {reason}.",
        forced=forced
    )

    session.delete(re)

    return True