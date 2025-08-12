# bot/services/events_service.py
from typing import Iterable
from db.database import db_session
from db.schema import EventStatus
from bot.crud.events_crud import (
    search_events, EventFilter,
    get_event_by_key, get_event_message_refs_by_key
)
from bot.domain.mapping import event_to_dto
from bot.domain.dto import EventDTO, EventMessageRefsDTO

# --- Generic finder ----------------------------------------------------------
def find_events_dto(
    *,
    status_in: tuple[EventStatus, ...] | None = None,
    types_in: tuple[str, ...] | None = None,
    coordinator_ids: tuple[str, ...] | None = None,
    has_embed: bool | None = None,
    start_date_min: str | None = None,
    start_date_max: str | None = None,
    priority_min: int | None = None,
    priority_max: int | None = None,
    search_name_icontains: str | None = None,
    tags_any: Iterable[str] | None = None,
    tags_all: Iterable[str] | None = None,
    limit: int | None = 25,
    offset: int | None = None,
    order_by_priority_then_date: bool = True,
) -> list[EventDTO]:
    with db_session() as s:
        rows = search_events(
            s,
            EventFilter(
                status_in=status_in,
                types_in=types_in,
                coordinator_ids=coordinator_ids,
                has_embed=has_embed,
                start_date_min=start_date_min,
                start_date_max=start_date_max,
                priority_min=priority_min,
                priority_max=priority_max,
                search_name_icontains=search_name_icontains,
                order_by_priority_then_date=order_by_priority_then_date,
                limit=limit,
                offset=offset,
            ),
        )

        # --- Post-filter by tags (CSV in schema) until normalized -------------
        if tags_any or tags_all:
            tags_any_l = {t.strip().lower() for t in (tags_any or []) if t.strip()}
            tags_all_l = {t.strip().lower() for t in (tags_all or []) if t.strip()}

            def tag_tokens(csv: str | None) -> set[str]:
                if not csv:
                    return set()
                return {t.strip().lower() for t in csv.split(",") if t.strip()}

            def ok(ev) -> bool:
                toks = tag_tokens(ev.tags)
                if tags_any_l and not (toks & tags_any_l):
                    return False
                if tags_all_l and not tags_all_l.issubset(toks):
                    return False
                return True

            rows = [ev for ev in rows if ok(ev)]

        return [event_to_dto(ev) for ev in rows]

# --- Common user-facing helpers ----------------------------------------------
def list_user_browseable_events(limit: int = 25) -> list[EventDTO]:
    
    return find_events_dto(
        status_in=(EventStatus.visible, EventStatus.active),
        has_embed=True,
        limit=limit,
    )

def list_user_reporting_events(limit: int = 25) -> list[EventDTO]:
    
    return find_events_dto(
        status_in=(EventStatus.visible, EventStatus.active),
        limit=limit,
    )

def list_user_archived_events(limit: int = 25, tags_any: Iterable[str] | None = None) -> list[EventDTO]:
    
    return find_events_dto(
        status_in=(EventStatus.archived,),
        tags_any=tags_any,
        limit=limit,
    )

# --- Direct lookups / projections --------------------------------------------
def get_event_dto_by_key(event_key: str) -> EventDTO | None:
    with db_session() as s:
        ev = get_event_by_key(s, event_key)
        return event_to_dto(ev) if ev else None
    
def get_event_message_refs_dto(event_key: str) -> EventMessageRefsDTO | None:
    with db_session() as s:
        refs = get_event_message_refs_by_key(s, event_key)
        if not refs:
            return None
        return EventMessageRefsDTO(
            event_key=refs.event_key,
            event_name=refs.event_name,
            embed_channel_discord_id=refs.embed_channel_discord_id,
            embed_message_discord_id=refs.embed_message_discord_id
        )