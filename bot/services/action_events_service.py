# bot/services/action_events_service.py
from __future__ import annotations

from sqlalchemy.orm import Session
from db.database import db_session

from bot.domain.dto import ActionEventDTO
from bot.domain.mapping import to_action_event_dto

from bot.crud.action_events_crud import list_self_reportable_action_events_for_event, user_already_completed_non_repeatable, list_action_events_for_event, get_action_event_bundle

from bot.services.events_service import get_event_is_open_for_action
from bot.services.users_service import get_or_create_user_dto

def list_user_doable_action_events(
    session: Session,
    member,
    event_id: int,
) -> list[ActionEventDTO]:
    """
    Return ActionEventDTOs the user can self-report for the given event.
    CRUD enforces: Action active, is_self_reportable.
    Service enforces: event status gating + repeatability.
    """
    user = get_or_create_user_dto(session, member)

    rows = list_self_reportable_action_events_for_event(session, event_id)
    out: list[ActionEventDTO] = []

    for ae, action, revent, ev in rows:
        dto = to_action_event_dto(ae, action, revent)
        if not get_event_is_open_for_action(
                ev, allowed_during_visible=ae.is_allowed_during_visible):
            continue
        if not dto.is_repeatable:
            if user_already_completed_non_repeatable(session, user.id, dto.id):
                continue
        out.append(dto)

    out.sort(key=lambda d: (d.action_description.lower(), d.variant.lower()))
    return out

def list_action_events_for_event_dto(event_id: int) -> list[ActionEventDTO]:

    with db_session() as session:
        rows = list_action_events_for_event(session, event_id)
        out: list[ActionEventDTO] = []
    
        for ae, action, revent, ev in rows:
            dto = to_action_event_dto(ae, action, revent)
            out.append(dto)
    
        out.sort(key=lambda d: (d.action_description.lower(), d.variant.lower()))
    return out

def get_action_event_dto_by_id (action_event_id: int) -> ActionEventDTO | None:
    with db_session() as session:
        ae, action, revent, ev = get_action_event_bundle(session, action_event_id)
        if ae:
            return to_action_event_dto(ae, action, revent)
    return None