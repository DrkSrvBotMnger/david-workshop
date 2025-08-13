from dataclasses import dataclass
import discord
from db.database import db_session
from bot.services.events_service import list_user_reporting_events, get_event_dto_by_key
from bot.services.action_events_service import list_user_doable_action_events
from bot.services.user_actions_service import submit_user_action
from bot.domain.dto import ActionEventDTO, UserActionCreateDTO, ActionReportResultDTO

@dataclass(frozen=True)
class EventOptionVM:
    id: int
    key: str
    name: str
    status: str
    start: str | None
    end: str | None

@dataclass(frozen=True)
class ActionOptionVM:
    id: int
    label: str
    description: str
    input_fields: list[str]
    input_help_map: dict[str, str]

@dataclass(frozen=True)
class EventPickVM:
    value: str          # event_key
    label: str          # event_name
    description: str    # status + dates

def to_event_pick_vm(ev) -> EventPickVM:
    status = str(ev.event_status)
    start = ev.start_date or "??"
    end = ev.end_date or "??"
    return EventPickVM(
        value=ev.event_key,
        label=ev.event_name,
        description=f"{status} • {start} → {end}",
    )

def get_event_pick_vms(limit: int = 25) -> list[EventPickVM]:
    """Return a list of EventPickVMs for browseable events (visible/active)."""
    with db_session() as s:
        rows = list_user_reporting_events(limit=limit)
    return [to_event_pick_vm(ev) for ev in rows]

def to_event_vm(ev) -> EventOptionVM:
    return EventOptionVM(
        id=ev.id, key=ev.event_key, name=ev.event_name,
        status=str(ev.event_status), start=ev.start_date, end=ev.end_date
    )

def to_action_vm(dto: ActionEventDTO, currency=":coin:") -> ActionOptionVM:
    label = dto.action_description
    if dto.variant and dto.variant.lower() != "default":
        label += f" ({dto.variant})"
    label += (" – 🏆" if dto.has_direct_reward else (f" – {dto.points_granted} {currency}" if dto.points_granted else ""))
    desc = (dto.input_help_map or {}).get("general", "")[:100]
    return ActionOptionVM(
        id=dto.id, label=label[:100], description=desc,
        input_fields=dto.input_fields, input_help_map=dto.input_help_map or {}
    )
    
def build_event_select_options(limit: int = 25) -> list[discord.SelectOption]:
    with db_session() as s:  # db handled here
        rows = list_user_reporting_events(limit=limit)
    opts: list[discord.SelectOption] = []
    for ev in rows:
        vm = to_event_vm(ev)
        label = vm.name[:100]
        desc = f"{vm.status} • {vm.start or '??'} → {vm.end or '??'}"[:100]
        opts.append(discord.SelectOption(label=label, value=vm.key, description=desc))
    return opts

def get_event_and_action_vms(member, event_key: str) -> tuple[EventOptionVM | None, list[ActionOptionVM]]:
    with db_session() as s:
        ev = get_event_dto_by_key(event_key)
        if not ev:
            return None, []
        dtos = list_user_doable_action_events(s, member, ev.id)
    return to_event_vm(ev), [to_action_vm(d) for d in dtos]

def submit_report_action_presentation(
    member,
    *,
    action_event_id: int,
    url_value: str | None,
    numeric_value: int | None,
    text_value: str | None,
    boolean_value: bool | None,
    date_value: str | None,
) -> ActionReportResultDTO | str:
    with db_session() as s:
        payload = UserActionCreateDTO(
            user_discord_id=str(member.id),
            action_event_id=action_event_id,
            url_value=url_value,
            numeric_value=numeric_value,
            text_value=text_value,
            boolean_value=boolean_value,
            date_value=date_value,
        )
        return submit_user_action(s, member, payload)
