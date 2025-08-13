# bot/services/user_actions_service.py
from __future__ import annotations

from sqlalchemy.orm import Session

from bot.domain.dto import ActionEventDTO, UserActionCreateDTO, ActionReportResultDTO
from bot.domain.mapping import to_action_event_dto

from bot.crud.action_events_crud import user_already_completed_non_repeatable, get_action_event_bundle
from bot.crud.inventory_crud import add_or_increment_inventory
from bot.crud.user_actions_crud import insert_user_action
from bot.crud.user_event_data_crud import get_or_create_user_event_data, add_points_to_user_event_data
from bot.crud.users_crud import add_points_to_user

from bot.services.action_events_service import get_event_is_open_for_action
from bot.services.events_service import get_status_name
from bot.services.rewards_service import get_reward_dto_by_reward_event_id, bump_reward_granted_counter
from bot.services.users_service import get_or_create_user_dto

# adjust this import to wherever your helper lives
from bot.utils.time_parse_paginate import now_iso

# ------------------ internal helpers --------------------

def _required_fields_present(ae: ActionEventDTO, payload: UserActionCreateDTO) -> str | None:
    if not ae.input_fields:
        return None
    missing: list[str] = []
    for f in ae.input_fields:
        if f == "url_value" and payload.url_value is None:
            missing.append("url_value")
        elif f == "numeric_value" and payload.numeric_value is None:
            missing.append("numeric_value")
        elif f == "text_value" and payload.text_value is None:
            missing.append("text_value")
        elif f == "boolean_value" and payload.boolean_value is None:
            missing.append("boolean_value")
        elif f == "date_value" and payload.date_value is None:
            missing.append("date_value")
    return "⚠️ Missing required field(s): " + ", ".join(missing) if missing else None

# -------------------- public API -------------------------

def submit_user_action(
    session: Session,
    member,
    payload: UserActionCreateDTO,
) -> ActionReportResultDTO | str:
    """
    Validate availability + rules, write logs/points/rewards, return result DTO.
    Returns a human error string on failure.
    """
    user = get_or_create_user_dto(session, member)

    bundle = get_action_event_bundle(session, payload.action_event_id)
    if not bundle:
        return "❌ Action not found."
    ae, action, revent, ev = bundle
    dto = to_action_event_dto(ae, action, revent)

    ev_status = get_status_name(ev)
    if not get_event_is_open_for_action(ev, allowed_during_visible=dto):
        return "⚠️ This action isn’t available right now."
    if not dto.is_self_reportable:
        return "⚠️ This action cannot be self‑reported."
    if not dto.is_repeatable:
        if user_already_completed_non_repeatable(session, user.id, dto.id):
            return "⚠️ You’ve already completed this action."

    # required fields (defense in depth; UI should already enforce)
    err = _required_fields_present(dto, payload)
    if err:
        return err

    # points calculation
    base = dto.points_granted or 0
    points_awarded = base
    numeric_applied = False
    if payload.numeric_value is not None:
        if payload.numeric_value < 0:
            return "⚠️ The number must be an integer ≥ 0."
        if dto.is_numeric_multiplier:
            points_awarded = base * payload.numeric_value
            numeric_applied = True

    ts = now_iso()

    # ensure per-event stats (set joined_at only on create)
    if ev is not None:
        get_or_create_user_event_data(
            session,
            user_id=user.id,
            event_id=ev.id,
            joined_at_if_create=ts,
            created_by_if_create=str(payload.user_discord_id),
        )

    # log the action
    insert_user_action(
        session,
        user_id=user.id,
        action_event_id=ae.id,
        event_id=ev.id if ev is not None else None,
        created_by=str(payload.user_discord_id),
        created_at=ts,
        url_value=payload.url_value,
        numeric_value=payload.numeric_value,
        text_value=payload.text_value,
        boolean_value=payload.boolean_value,
        date_value=payload.date_value,
    )

    # points
    if points_awarded:
        add_points_to_user(session, user.id, points_awarded)
        if ev is not None:
            add_points_to_user_event_data(session, user_id=user.id, event_id=ev.id, delta_points=points_awarded)

    # direct reward
    reward_name: str | None = None
    if ae.reward_event_id:
        reward_dto = get_reward_dto_by_reward_event_id(session, ae.reward_event_id)
        if reward_dto:
            add_or_increment_inventory(
                session,
                user_id=user.id,
                reward_id=reward_dto.id,
                is_stackable=reward_dto.is_stackable,
            )
            bump_reward_granted_counter(session, reward_dto.id, qty=1)
            reward_name = reward_dto.reward_name

    session.commit()

    action_label = f"{dto.action_description}" + (f" ({dto.variant})" if dto.variant else "")
    return ActionReportResultDTO(
        points_base=base,
        points_awarded=points_awarded,
        numeric_applied=numeric_applied,
        reward_name=reward_name,
        event_name=ev.event_name,
        action_label=action_label,
        numeric_value=payload.numeric_value,
        url_value=payload.url_value,
        text_value=payload.text_value,
        boolean_value=payload.boolean_value,
        date_value=payload.date_value,
    )