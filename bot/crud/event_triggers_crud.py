# bot/crud/event_triggers_crud.py
from sqlalchemy.orm import Session
from db.schema import EventTrigger, UserEventTriggerLog
from bot.utils.formatting import now_iso
from bot.utils.parsing import build_json_field

# ---------- EventTrigger CRUD ----------

def create_event_trigger(
    session: Session, 
    create_data: dict
) -> EventTrigger:
    """
    Always expect a dict with keys: event_id, trigger_type, config
    """
        
    trigger = EventTrigger(
        event_id=create_data.get("event_id"),
        trigger_type=create_data["trigger_type"],
        config_json=build_json_field(create_data["config"]),
        reward_event_id=None,
        points_granted=None,
        created_at=create_data.get("created_at", now_iso()),
    )
    session.add(trigger)
    session.flush()
    return trigger

def check_event_trigger_exists(session: Session, event_id: int, trigger_type: str, config_json: dict) -> EventTrigger | None:
    return session.query(EventTrigger).filter_by(event_id=event_id, trigger_type=trigger_type, config_json=build_json_field(config_json)).first()

def get_event_triggers_for_event(session: Session, event_id: int) -> list[EventTrigger]:
    return session.query(EventTrigger).filter_by(event_id=event_id).all()

def get_global_event_triggers(session: Session) -> list[EventTrigger]:
    return session.query(EventTrigger).filter(EventTrigger.event_id == None).all()

def get_event_trigger_by_id(session: Session, trigger_id: int) -> EventTrigger | None:
    return session.query(EventTrigger).get(trigger_id)

def update_event_trigger(
    session: Session, 
    trigger_id: int, 
    update_data: dict
) -> EventTrigger | None:
    trigger = get_event_trigger_by_id(session, trigger_id)
    if not trigger:
        return None
    if "config" in update_data:
        trigger.config_json = build_json_field(update_data["config"])
    for key, value in update_data.items():
        if key == "config":
            continue
        if hasattr(trigger, key):
            setattr(trigger, key, value)
    session.flush()
    return trigger

def delete_event_trigger(
    session: Session, 
    trigger_id: int
) -> bool:
    trigger = get_event_trigger_by_id(session, trigger_id)
    if not trigger:
        return False
    session.delete(trigger)
    session.flush()
    return True

# ---------- UserEventTriggerLog CRUD ----------

def log_event_trigger_grant(
    session: Session, 
    user_id: int, 
    trigger_id: int
) -> UserEventTriggerLog:
    log = UserEventTriggerLog(
        user_id=user_id,
        event_trigger_id=trigger_id,
        granted_at=now_iso(),
    )
    session.add(log)
    session.flush()
    return log

def get_user_event_trigger_logs(session: Session, user_id: int) -> list[UserEventTriggerLog]:
    return session.query(UserEventTriggerLog).filter_by(user_id=user_id).all()

def has_user_event_trigger_log(session: Session, user_id: int, trigger_id: int) -> bool:
    return (
        session.query(UserEventTriggerLog)
        .filter_by(user_id=user_id, event_trigger_id=trigger_id)
        .first()
        is not None
    )

def delete_user_event_trigger_log(session: Session, log_id: int) -> bool:
    log = session.query(UserEventTriggerLog).get(log_id)
    if not log:
        return False
    session.delete(log)
    session.flush()
    return True