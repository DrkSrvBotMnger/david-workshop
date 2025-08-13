# bot/crud/user_actions_crud.py
from __future__ import annotations
from sqlalchemy.orm import Session
from db.schema import UserAction

def insert_user_action(
    session: Session,
    *,
    user_id: int,
    action_event_id: int,
    event_id: int | None,
    created_by: str,
    created_at: str,                 
    url_value: str | None = None,
    numeric_value: int | None = None,
    text_value: str | None = None,
    boolean_value: bool | None = None,
    date_value: str | None = None,
) -> UserAction:
    ua = UserAction(
        user_id=user_id,
        action_event_id=action_event_id,
        event_id=event_id,
        created_by=created_by,
        created_at=created_at,
        url_value=url_value,
        numeric_value=numeric_value,
        text_value=text_value,
        boolean_value=boolean_value,
        date_value=date_value,
    )
    session.add(ua)
    session.flush()
    return ua