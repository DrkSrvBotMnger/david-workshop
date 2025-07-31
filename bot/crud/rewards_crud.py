from sqlalchemy import or_
from sqlalchemy.orm import Session
from bot.crud import general_crud
from bot.utils import now_iso
from db.schema import Reward, RewardLog, RewardEvent, Event


# --- CREATE ---
def create_reward(session: Session, reward_data: dict, performed_by: str) -> Reward:
    """
    Create a new reward.
    reward_data should match Reward model fields except id.
    """
    reward = Reward(**reward_data, created_at=now_iso())
    session.add(reward)
    session.flush()  # Needed to get reward.id for log

    general_crud.log_change(
        session=session,
        log_model=RewardLog,
        fk_field="reward_id",
        fk_value=reward.id,
        action="create",
        performed_by=performed_by,
        description=f"Reward created: {reward.reward_name} ({reward.reward_id})"
    )
    return reward
    

# --- UPDATE ---
def update_reward(session: Session, reward_id: str, updates: dict, performed_by: str) -> Reward:
    """
    Update a reward with the given updates dict.
    Returns updated Reward or None if not found.
    """
    reward = get_reward(session, reward_id)
    if not reward:
        return None

    for key, value in updates.items():
        setattr(reward, key, value)

    reward.modified_by = performed_by
    reward.modified_at = now_iso()

    general_crud.log_change(
        session=session,
        log_model=RewardLog,
        fk_field="reward_id",
        fk_value=reward.id,
        action="edit",
        performed_by=performed_by,
        description=f"Updated fields: {', '.join(updates.keys())}",
        forced=True
    )

    return reward


# --- DELETE ---
def delete_reward(session: Session, reward_id: str, performed_by: str) -> bool:
    """Delete a reward and log the action."""
    reward = get_reward(session, reward_id)
    if not reward:
        return False

    general_crud.log_change(
        session=session,
        log_model=RewardLog,
        fk_field="reward_id",
        fk_value=reward.id,
        action="delete",
        performed_by=performed_by,
        description=f"Deleted reward: {reward.reward_name} ({reward.reward_id})",
        forced=True
    )

    session.delete(reward)
    return True


# --- PUBLISH ---
def publish_preset(
    session: Session,
    reward_id: str,
    use_channel_id: str,
    use_message_id: str,
    use_header_message_id: str, 
    set_by: str
) -> Reward:
    """
    Update a reward's approved preset details.
    Also logs the publish action.
    """
    reward = get_reward(session, reward_id)
    if not reward:
        return None

    reward.use_channel_id = str(use_channel_id)
    reward.use_message_id = str(use_message_id)
    reward.use_header_message_id = str(use_header_message_id)  # header
    reward.preset_set_by = str(set_by)
    reward.preset_set_at = now_iso()

    reward.modified_by = set_by
    reward.modified_at = reward.preset_set_at

    general_crud.log_change(
        session=session,
        log_model=RewardLog,
        fk_field="reward_id",
        fk_value=reward.id,
        action="edit",
        performed_by=set_by,
        description=f"Published/updated preset for reward `{reward.reward_id}`.",
        forced=True
    )

    return reward


# --- GET ---
def get_reward(session: Session, reward_id: str) -> Reward:
    """Retrieve a reward by its internal reward_id."""
    return session.query(Reward).filter_by(reward_id=reward_id).first()


# --- LIST ---
def get_all_rewards(
    session,
    type: str = None,
    mod_id: str = None,
    name: str = None
):
    """
    Retrieve rewards with optional filters:
    - reward_type: 'title', 'badge', 'preset'
    - reward_name: partial match on reward name
    - mod_id: Discord ID of moderator
    """
    query = session.query(Reward)

    if type:
        query = query.filter(Reward.reward_type.ilike(type))
    if name:
        query = query.filter(Reward.reward_name.ilike(f"%{name}%"))
    if mod_id:
        query = query.filter(
            or_(Reward.created_by == mod_id, Reward.modified_by == mod_id)
        )

    return query.order_by(
        Reward.modified_at.desc().nullslast(),
        Reward.created_at.desc()
    ).all()


# --- LIST LOGS ---
def get_reward_logs(
    session,
    action: str = None,
    performed_by: str = None
):
    """
    Retrieve reward logs with optional filters:
    - action: 'create', 'edit', 'delete'
    - performed_by: Discord ID of moderator
    """
    query = (
        session.query(RewardLog)
        .join(Reward, Reward.id == RewardLog.reward_id, isouter=True)
    )

    if action:
        query = query.filter(RewardLog.action == action.lower())
    if performed_by:
        query = query.filter(RewardLog.performed_by == performed_by)

    return query.order_by(RewardLog.timestamp.desc()).all()


# --- VALIDATE ---
def reward_is_linked_to_active_event(session, reward_code: str) -> bool:
    """
    Checks if the given reward (by public string reward_id) is linked
    to at least one active event.

    reward_code: str -> e.g. "p_drkweek"
    Returns: bool
    """

    # First, find the Reward object from its public string ID
    reward = session.query(Reward).filter(Reward.reward_id == reward_code).first()
    if not reward:
        return False  # No such reward exists

    # Then check if this reward's integer PK is linked to any active events
    return (
        session.query(RewardEvent)
        .join(Event, Event.id == RewardEvent.event_id)
        .filter(
            RewardEvent.reward_id == reward.id,  # integer PK now
            Event.active.is_(True)
        )
        .count()
        > 0
    )

