# bot/presentation/event_triggers_presentation.py
from discord import SelectOption
from bot.services.events_service import find_events_dto
from bot.services.reward_events_service import get_reward_events_for_event_service
from bot.services.prompts_service import list_event_prompts
from bot.services.action_events_service import list_action_events_for_event_dto
from bot.config.constants import TRIGGER_TYPES 
from bot.ui.common.selects import build_select_options_from_vms

def make_event_options(event_type_filter=None, status_filter=None):
    # Optionally filter events by type/status before display
    events = find_events_dto(status_in=status_filter or None, types_in=event_type_filter or None, limit=50)
    return build_select_options_from_vms(
        events,
        get_value=lambda ev: ev.id,
        get_label=lambda ev: f"{ev.event_name} ({ev.event_type})",
        get_description=lambda ev: (ev.event_description or "")[:100],
    )

def make_reward_event_options(event_id):
    rewards = get_reward_events_for_event_service(event_id)
    return build_select_options_from_vms(
        rewards,
        get_value=lambda re: re.id,
        get_label=lambda re: re.reward_name,
        get_description=lambda re: f"{re.availability} — {re.reward_type}"
    )

def make_prompt_options(event_id):
    prompts = list_event_prompts(event_id)
    if not prompts:
        return [SelectOption(label="No prompts available", value="none", default=True, description=None)]

    return build_select_options_from_vms(
        prompts,
        get_value=lambda p: p.code,
        get_label=lambda p: p.label,
        get_description=lambda p: f"{p.group} — {p.code}"
    )

def make_ae_options(event_id):
    actions = list_action_events_for_event_dto(event_id)
    if not actions:
        return [SelectOption(label="No action-events found", value="none", default=True, description=None)]
    return build_select_options_from_vms(
        actions,
        get_value=lambda ae: ae.id,
        get_label=lambda ae: ae.action_description,
        get_description=lambda ae: f"{ae.variant}"
    )

def get_available_trigger_types(event_type: str) -> list[tuple[str, str, str]]:
    """
    Returns list of (trigger_key, description) tuples based on event_type.
    """
    result = []
    for key, group, label, description in TRIGGER_TYPES:
        if event_type == "global":
            if group == "global":
                result.append((key, label, description))
        else:
            if group == "all" or group == event_type:
                result.append((key, label, description))
    return result

def make_trigger_type_options(event_type: str) -> list[SelectOption]:
    return [
        SelectOption(
            label=label,
            value=key,
            description=description
        ) for key, label, description in get_available_trigger_types(event_type)
    ]