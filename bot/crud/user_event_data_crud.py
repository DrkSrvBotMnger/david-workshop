# bot/crud/user_event_data_crud.py
from sqlalchemy.orm import Session
from db.schema import UserEventData

def get_or_create_user_event_data(
    session: Session, *, user_id: int, event_id: int, joined_at_if_create: str, created_by_if_create: str
) -> UserEventData:
    ued = session.query(UserEventData).filter(UserEventData.user_id == user_id, UserEventData.event_id == event_id).first()
    if ued:
        return ued
    ued = UserEventData(
        user_id=user_id, event_id=event_id, points_earned=0,
        joined_at=joined_at_if_create, created_by=created_by_if_create
    )
    session.add(ued)
    session.flush()
    return ued

def add_points_to_user_event_data(session: Session, *, user_id: int, event_id: int, delta_points: int) -> None:
    if not delta_points:
        return
    ued = session.query(UserEventData).filter(UserEventData.user_id == user_id, UserEventData.event_id == event_id).first()
    if not ued:
        return  # caller must ensure creation first
    ued.points_earned = (ued.points_earned or 0) + delta_points
    session.flush()