from dataclasses import dataclass

@dataclass(frozen=True)
class UserDTO:
    id: int
    user_discord_id: str
    points: int
    total_earned: int
    total_spent: int
    username: str | None
    display_name: str | None
    nickname: str | None

@dataclass(frozen=True)
class EventDTO:
    id: int
    event_key: str
    event_name: str
    event_type: str
    event_description: str
    start_date: str
    end_date: str | None
    coordinator_discord_id : str | None
    priority: int
    tags: str | None
    embed_channel_discord_id: str | None
    embed_message_discord_id: str | None
    role_discord_id: str | None
    event_status: str

@dataclass(frozen=True)
class EventMessageRefsDTO:
    event_key: str
    event_name: str
    embed_channel_discord_id: str
    embed_message_discord_id: str