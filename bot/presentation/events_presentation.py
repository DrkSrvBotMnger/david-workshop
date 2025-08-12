# bot/services/events_service.py
from dataclasses import dataclass
from typing import Callable
from bot.domain.dto import EventDTO, EventMessageRefsDTO

# ------------------------------
# VM (what the UI will consume)
# ------------------------------
@dataclass(frozen=True)
class EventOptionVM:
    value: str        # event_key
    label: str        # text shown in the select
    description: str  # smaller line under the label

@dataclass(frozen=True)
class EventMessageVM:
    event_key: str
    title: str           # event name
    channel_id: str      # Discord channel ID (as string)
    message_id: str      # Discord message ID (as string)
    message_url: str     # convenience; not required by the UI

# ------------------------------------------------------
# Formatter = how to turn ONE EventDTO into two strings
# ------------------------------------------------------
# Signature: (EventDTO) -> (label, description)
EventFormatter = Callable[[EventDTO], tuple[str, str]]

def event_default_fmt(d: EventDTO) -> tuple[str, str]:
    # Minimal and clear: name as label, type as description
    return d.event_name, d.event_type

def event_with_status_fmt(d: EventDTO) -> tuple[str, str]:
    # Add status (draft/visible/active/archived)
    return d.event_name, f"{d.event_type} • {d.event_status}"

def event_with_dates_fmt(d: EventDTO) -> tuple[str, str]:
    # Show type and the date range
    end = d.end_date or "?"
    return d.event_name, f"{d.event_type} • {d.start_date} → {end}"

def event_compact_admin_fmt(d: EventDTO) -> tuple[str, str]:
    # A compact admin-friendly line with more context
    end = d.end_date or "?"
    return d.event_name, f"{d.event_type} • {d.event_status} • {d.start_date} → {end}"

# -------------------------------------------------------------------
# Mapper = apply the formatter to a LIST of DTOs to build the VMs
# -------------------------------------------------------------------
def make_event_options(
    dtos: list[EventDTO],
    fmt: EventFormatter = event_default_fmt
) -> list[EventOptionVM]:
    vms: list[EventOptionVM] = []
    for d in dtos:
        label, desc = fmt(d)
        
        vms.append(EventOptionVM(value=d.event_key, label=label, description=desc))
    return vms

def make_event_message_vm(refs: EventMessageRefsDTO, guild_id: int) -> EventMessageVM:
    url = f"https://discord.com/channels/{guild_id}/{refs.embed_channel_discord_id}/{refs.embed_message_discord_id}"
    return EventMessageVM(
        event_key=refs.event_key,
        title=refs.event_name,
        channel_id=refs.embed_channel_discord_id,
        message_id=refs.embed_message_discord_id,
        message_url=url,
    )