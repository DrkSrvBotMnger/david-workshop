# bot/services/prompts_service.py
from typing import Iterable, Optional, Sequence
from db.database import db_session
from bot.crud.prompts_crud import (
    get_prompts_for_event as crud_get_prompts_for_event,
    upsert_prompts_bulk as crud_upsert_prompts_bulk,
    update_prompt as crud_update_prompt,
    delete_prompt_safe as crud_delete_prompt_safe,
    replace_user_action_prompts as crud_replace_user_action_prompts,
    get_prompts_for_action_event_picker as crud_get_prompts_for_action_event_picker,
    count_prompt_popularity_for_event as crud_count_prompt_popularity_for_event,
    count_user_prompt_stats_for_event as crud_count_user_prompt_stats_for_event,
)
from bot.domain.dto import (
    EventPromptDTO,
    UserActionPromptDTO,
    PromptPopularityDTO,
    UserPromptStatsDTO,
)
from bot.domain.mapping import (
    event_prompt_to_dto,
    user_action_prompt_to_dto,
    popularity_row_to_dto,
)

# -------- Event prompts --------

def list_event_prompts(
    event_id: int,
    group: Optional[str] = None,
    active_only: bool = True,
) -> list[EventPromptDTO]:
    with db_session() as session:
        rows = crud_get_prompts_for_event(session, event_id, group, active_only)
        return [event_prompt_to_dto(r) for r in rows]

def upsert_event_prompts_bulk(
    *,
    event_id: int,
    group: Optional[str],
    labels_in_order: Sequence[str],
    created_by: str,
    created_at: str,
) -> list[EventPromptDTO]:
    with db_session() as session:
        rows = crud_upsert_prompts_bulk(
            session,
            event_id=event_id,
            group=group,
            labels_in_order=labels_in_order,
            created_by=created_by,
            created_at=created_at,
        )
        return [event_prompt_to_dto(r) for r in rows]

def edit_event_prompt(
    prompt_id: int,
    *,
    label: Optional[str] = None,
    is_active: Optional[bool] = None,
    day_index: Optional[int] = None,
    group: Optional[str] = None,
    modified_by: Optional[str] = None,
    modified_at: Optional[str] = None,
) -> EventPromptDTO | None:
    with db_session() as session:
        row = crud_update_prompt(
            session,
            prompt_id,
            label=label,
            is_active=is_active,
            day_index=day_index,
            group=group,
            modified_by=modified_by,
            modified_at=modified_at,
        )
        return event_prompt_to_dto(row) if row else None

def delete_event_prompt_if_unused(prompt_id: int) -> bool:
    with db_session() as session:
        return crud_delete_prompt_safe(session, prompt_id)

# -------- User action <-> prompts --------

def set_user_action_prompts(
    *,
    user_action_id: int,
    event_prompt_ids: Iterable[int],
) -> list[UserActionPromptDTO]:
    with db_session() as session:
        rows = crud_replace_user_action_prompts(
            session,
            user_action_id=user_action_id,
            event_prompt_ids=event_prompt_ids,
        )
        return [user_action_prompt_to_dto(r) for r in rows]

def picker_prompts_for_action_event(action_event_id: int) -> list[EventPromptDTO]:
    with db_session() as session:
        rows = crud_get_prompts_for_action_event_picker(session, action_event_id)
        return [event_prompt_to_dto(r) for r in rows]

# -------- Reporting --------

def prompt_popularity(event_id: int) -> list[PromptPopularityDTO]:
    with db_session() as session:
        rows = crud_count_prompt_popularity_for_event(session, event_id)
        return [popularity_row_to_dto(r) for r in rows]

def user_prompt_stats(event_id: int, user_id: int) -> UserPromptStatsDTO:
    with db_session() as session:
        total, unique_ = crud_count_user_prompt_stats_for_event(session, event_id, user_id)
        return UserPromptStatsDTO(
            event_id=event_id,
            user_id=user_id,
            total_tagged=total,
            unique_prompts=unique_,
        )

