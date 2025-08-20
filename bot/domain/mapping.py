# bot/domain/mapping.py
from typing import Tuple
from db.schema import (
    Event as EventModel, 
    User as UserModel, 
    Action as ActionModel, 
    Reward as RewardModel, 
    EventPrompt as EventPromptModel, 
    UserActionPrompt as UserActionPromptModel, 
    ActionEvent as ActionEventModel,
    RewardEvent as RewardEventModel, 
    EventTrigger as EventTriggerModel, 
    UserEventTriggerLog as UserEventTriggerLogModel
)
from bot.domain.dto import (
    UserDTO, EventDTO, 
    ActionEventDTO,
    RewardGrantDTO,
    EventPromptDTO,
    UserActionPromptDTO,
    PromptPopularityDTO,
    EventTriggerDTO, UserEventTriggerLogDTO
)
from bot.utils.parsing import parse_required_fields, parse_help_texts, parse_json_field

def user_to_dto(u: UserModel) -> UserDTO:
    return UserDTO(
        id=u.id, 
        user_discord_id=u.user_discord_id,
        points=u.points,
        total_earned=u.total_earned,
        total_spent=u.total_spent,
        username=u.username,
        display_name=u.display_name, 
        nickname=u.nickname,
    )

def event_to_dto(ev: EventModel) -> EventDTO:
    return EventDTO(
        id=ev.id,
        event_key=ev.event_key,
        event_name=ev.event_name,
        event_type=ev.event_type,
        event_description=ev.event_description,
        start_date=ev.start_date,
        end_date=ev.end_date,
        coordinator_discord_id=ev.coordinator_discord_id,
        priority=ev.priority or 0,
        tags=ev.tags,
        embed_channel_discord_id=ev.embed_channel_discord_id,
        embed_message_discord_id=ev.embed_message_discord_id,
        role_discord_id=ev.role_discord_id,
        event_status=ev.event_status.value,
    )
    
def reward_to_grant_dto(r: RewardModel) -> RewardGrantDTO:
    return RewardGrantDTO(
        id=r.id,
        reward_name=r.reward_name,
        is_stackable=bool(r.is_stackable),
    )
    
def event_prompt_to_dto(ep: EventPromptModel) -> EventPromptDTO:
    return EventPromptDTO(
        id=ep.id,
        event_id=ep.event_id,
        group=ep.group,
        day_index=ep.day_index,
        code=ep.code,
        label=ep.label,
        is_active=ep.is_active,
        created_by=ep.created_by,
        created_at=ep.created_at,
        modified_by=ep.modified_by,
        modified_at=ep.modified_at,
    )

def user_action_prompt_to_dto(uap: UserActionPromptModel) -> UserActionPromptDTO:
    return UserActionPromptDTO(
        id=uap.id,
        user_action_id=uap.user_action_id,
        event_prompt_id=uap.event_prompt_id,
    )

def popularity_row_to_dto(row: Tuple[EventPromptModel, int]) -> PromptPopularityDTO:
    ep, uses = row
    return PromptPopularityDTO(
        event_id=ep.event_id,
        prompt_id=ep.id,
        prompt_code=ep.code,
        prompt_label=ep.label,
        uses=int(uses),
    )

def to_action_event_dto(ae: ActionEventModel, action: ActionModel, revent: RewardEventModel | None) -> ActionEventDTO:
    fields = parse_required_fields(action.input_fields_json)
    help_map = parse_help_texts(ae.input_help_json, fields)

    action_is_active = bool(action.is_active) and (action.deactivated_at is None)

    return ActionEventDTO(
        id=ae.id,
        action_event_key=ae.action_event_key,
        event_id=ae.event_id,
        action_id=ae.action_id,
        action_description=action.action_description,
        variant=ae.variant,

        input_fields=fields,
        input_help_map=help_map,

        is_self_reportable=bool(ae.is_self_reportable),
        is_repeatable=bool(ae.is_repeatable),
        is_allowed_during_visible=bool(ae.is_allowed_during_visible),
        action_is_active=action_is_active,
        is_numeric_multiplier=bool(ae.is_numeric_multiplier),

        points_granted=ae.points_granted or 0,
        has_direct_reward=bool(revent),

        prompts_required=bool(getattr(ae, "prompts_required", False)),
        prompts_group=getattr(ae, "prompts_group", None),
    )

def to_event_trigger_dto(et: EventTriggerModel) -> EventTriggerDTO:
    return EventTriggerDTO(
        id=et.id,
        event_id=et.event_id,
        trigger_type=et.trigger_type,
        config=parse_json_field(et.config_json),
        reward_event_id=et.reward_event_id,
        points_granted=et.points_granted,
        created_at=et.created_at,
    )

def to_user_event_trigger_log_dto(uetl: UserEventTriggerLogModel) -> UserEventTriggerLogDTO:
    return UserEventTriggerLogDTO(
        id=uetl.id,
        user_id=uetl.user_id,
        event_trigger_id=uetl.event_trigger_id,
        granted_at=uetl.granted_at,
    )